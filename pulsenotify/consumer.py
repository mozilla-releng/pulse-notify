import json
import logging
import os
from importlib import import_module
from yaml import safe_load
from json import JSONDecodeError
import aiohttp
from pulsenotify.util import fetch_task, retry_connection, RetriesExceededError
from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)

#  Exchanges to consume messages from
EXCHANGES = {
    # "exchange/taskcluster-queue/v1/task-defined",
    # "exchange/taskcluster-queue/v1/task-pending",
    # "exchange/taskcluster-queue/v1/task-running",
    # "exchange/taskcluster-queue/v1/artifact-created",
    "exchange/taskcluster-queue/v1/task-completed",
    "exchange/taskcluster-queue/v1/task-failed",
    "exchange/taskcluster-queue/v1/task-exception",
}

#  Keys to bind exchanges to
ROUTING_KEYS = os.environ['ROUTING_KEYS'].split(':')


class TaskFetchFailedError(Exception):
    """ Exception thrown when task fetch fails """
    pass


class NoLogsExistError(Exception):
    """ Exception thrown when no log exist for the given task """
    pass


class NoNotificationConfigurationError(Exception):
    """ Exception thrown when no notifications are configured """
    pass


class StatusNotificationsNotConfiguredError(Exception):
    """ Exception thrown when notifications not configured for a specific task status """
    pass


class InvalidStatusConfigurationError(Exception):
    """ Exception thrown when status notifications are incorrectly configured """
    pass


class NotifyConsumer(object):

    def __init__(self):
        #  Initializing the consumer means creating the mapping for the notification plugins.
        #  The list of plugins to use is pulled from the environment config (colon separated).
        #  The Plugin objects are constructed by importing the name from the plugins module and adding to
        #  the notifiers mapping.
        services_list = os.environ['PN_SERVICES'].split(':')

        self.notifiers = {}
        for service in services_list:
            try:
                self.notifiers[service] = import_module('pulsenotify.plugins.' + service).Plugin()
                assert hasattr(self.notifiers[service], 'notify')

            except ImportError:
                log.exception('No plugin named %s, initialization failed', service)

        #  Identities contain information about how to notify a single group/person/'identity'.
        #  The identities are pulled in from a yaml file. If an identity is present in the 'ids' section of a
        #  notification configuration, the information for that id will add and overwrite the initial configuration.
        id_config_path = '{curdir}/pulsenotify/id_configs/{id_env}.yml'.format(curdir=os.path.curdir,
                                                                               id_env=os.environ['ID_ENV'])
        self.identities = safe_load(open(id_config_path, 'r'))

        #  If a user does not want to notify based on ids and instead wants to specify the notification details fully
        #  within the task, they should be able to do so. This is accomplished by adding a 'default' identity with no
        #  information to the list. When the notification configurations are created, the default configuration will
        #  always be added to the list with no overwriting.
        self.identities = {**{'default': {}}, **self.identities}

        log.debug('IDs: %s', ', '.join(self.identities.keys()))
        log.info('Consumer initialized.')

    @property
    def exchanges(self):
        return EXCHANGES

    @property
    def routing_keys(self):
        return ROUTING_KEYS

    @async_time_me
    async def dispatch(self, channel, body, envelope, properties):
        task_data = TaskData(body, envelope, properties)

        try:
            await task_data.fetch_task_and_analyze()

            notify_sections = self.generate_notification_configurations(task_data)

            for id_name, id_section in notify_sections.items():
                if 'plugins' in id_section:
                    enabled_plugins = id_section['plugins']
                else:
                    log.debug('No plugins section found for %s, id %s', task_data, id_name)
                    continue

                for plugin_name in enabled_plugins:
                    if plugin_name in self.notifiers:
                        await self.notifiers[plugin_name].notify(task_data, id_section)
                    else:
                        log.warn('No plugin object %s for %r found in consumer.notifiers', plugin_name, task_data)

        except NoNotificationConfigurationError:
            log.exception('%s has no notifications section.', task_data)

        except InvalidStatusConfigurationError:
            log.exception('%r has a notifications section, but no notification configurations', task_data)

        except StatusNotificationsNotConfiguredError:
            log.warning('No configuration defined for status "{}" in task "{}". Skipping notification...'.format(
                task_data.status, task_data.id
            ))

        except TaskFetchFailedError:
            log.exception('Could not fetch %r', task_data)

        except NoLogsExistError as e:
            # Cancelled tasks may not have logs if they have never started. This happens when
            # we have to cancel a release graph. Hence, log.exception() is too high for this case.
            log.warn('Could not fetch logs for %r. Reason: %s', task_data, e)

        except Exception as e:
            log.exception('Exception %s caught by generic exception trap', e)

        finally:
            log.info('Acknowledging consumption of %r', task_data)
            return await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)

    def generate_notification_configurations(self, task_data):
        #  Retrieve the notifications section out of the task
        try:
            notification_section = task_data.definition['extra']['notifications']
        except KeyError as ke:
            raise NoNotificationConfigurationError() from ke

        #  Retrieve the notification configuration for this task status
        try:
            original_configuration = notification_section[task_data.status]

            if not isinstance(original_configuration, dict):
                raise InvalidStatusConfigurationError()

        except KeyError as ke:
            raise StatusNotificationsNotConfiguredError() from ke

        except TypeError as te:
            raise NoNotificationConfigurationError() from te

        #  This section creates the mapping of identities to the corresponding notification configurations for a
        #  task, where key is the id name and value is the configuration. original_configuration is the configuration
        #  for the task status the service is notifying for, pulled directly from the task definition. For each id
        #  present in both the original configuration and the service's list of ids, we create a notification
        #  configuration and add it to the mapping. We also always add the 'default' id to the mapping in case the user
        #  has already configured notifications in the task without ids.
        ids_in_original_config = original_configuration.get('ids', {})
        return {
                id_name: {**original_configuration, **id_config}
                for id_name, id_config in self.identities.items()
                if id_name in ids_in_original_config or id_name is 'default'
        }


class TaskData(object):

    S3_DESTINATION = 'https://{bucket}.s3.amazonaws.com/{log_key}'
    S3_KEY_TEMPLATE = '{branch}/{product}-{version}/build{build_number}/{name}-{platform}-{task_id}-{run_id}'
    LOG_TEMPLATES = {
        'buildbot-bridge':
            'https://queue.taskcluster.net/v1/task/{task_id}/runs/{run_id}/artifacts/public/properties.json',

        'aws-provisioner-v1':
            'https://queue.taskcluster.net/v1/task/{task_id}/runs/{run_id}/artifacts/public/logs/live.log',
    }

    def __init__(self, body, envelope, properties):
        self.body = json.loads(body.decode("utf-8"))
        self.envelope = envelope
        self.properties = properties
        self.id = self.body['status']['taskId']
        self.provisioner_id = self.body['status']['provisionerId']
        self.task_group_id = self.body['status']['taskGroupId']
        self.status = envelope.exchange_name.split('/')[-1]
        self.inspector_url = "https://tools.taskcluster.net/task-inspector/#{task_id}".format(task_id=self.id)

        #  These fields are created by the async function fetch_task_and_analyze
        self.definition = None
        self.logs = None

    def __repr__(self):
        return "Task(id={id}, status={status})".format(id=self.id, status=self.status)

    async def fetch_task_and_analyze(self):
        #  Fetch task, retrying a few times in case of a timeout
        #  Once the task is fetched, set as the definition and get the provisionerId
        try:
            self.definition = await retry_connection(fetch_task, self.id)
        except RetriesExceededError as e:
            raise TaskFetchFailedError from e

        #  No need to create the logs if the provisionerId is not supported
        if self.provisioner_id not in self.LOG_TEMPLATES:
            return

        #  Download the logs and store them in this object
        self.logs = []
        for run in self.body['status']['runs']:
            url = self.LOG_TEMPLATES[self.provisioner_id].format(task_id=self.id, run_id=run['runId'])
            #  Retry log grab in case of network instability
            try:
                # NoLogsExistError is raised only when we're sure the logs won't ever exist
                task_log = await retry_connection(
                    get_log, url, self.provisioner_id, by_pass_exceptions=(NoLogsExistError,)
                )
                self.logs.append((run['runId'], task_log,))
            except RetriesExceededError:
                log.warn('Could not retrieve log for %r run %s.', self, run)
                continue

    def log_data(self):
        build_properties = self.definition.get('extra', {}).get('build_props')
        if not build_properties:
            build_properties = self.definition.get('payload', {}).get('properties')
        if build_properties and self.logs:
            for run_number, data in self.logs:
                yield {
                    'data': data,
                    's3_key': self.make_s3_key(run_number, build_properties),
                    'destination_url': self.S3_DESTINATION.format(
                        bucket=os.environ['S3_BUCKET'],
                        log_key=self.make_s3_key(run_number, build_properties),
                    ),
                }

    def make_s3_key(self, run_id, build_properties):
        task_metadata = self.definition['metadata']

        #  The get call can still return None, which should be all for our purposes
        platform = build_properties.get('platform', 'all')
        if not platform:
            platform = 'all'

        name = task_metadata['name'].replace('/', '_').replace('\\', '_')

        s3_key = self.S3_KEY_TEMPLATE.format(branch=build_properties['branch'],
                                             product=build_properties['product'],
                                             version=build_properties['version'],
                                             build_number=build_properties['build_number'],
                                             name=name,
                                             platform=platform,
                                             task_id=self.id,
                                             run_id=run_id)

        s3_key = s3_key.replace(' ', '_')

        return s3_key


async def get_log(url, provisioner_id):
    #  Grabs logs for supported provisionerIds from a given url
    if provisioner_id == 'buildbot-bridge':
        return await get_bbb_log(url)

    elif provisioner_id == 'aws-provisioner-v1':
        return await get_aws_log(url)

    else:
        log.debug('Unknown provisionerId %s given to get_log', provisioner_id)
        return None


async def get_aws_log(url):
    #  Grabs log files for aws-provisioner tasks
    with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            log.debug('aws response header is: %s', response.headers.get('content-encoding', 'none'))
            return await response.text()


async def get_bbb_log(url):
    #  Grabs log files for buildbot-bridge provisioner tasks
    with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            log.debug('bbb response header is: %s', response.headers.get('content-encoding', 'none'))
            try:
                json_resp = await response.json()
                log.debug('bbb actual log filename: %s', json_resp['log_url'][0])
                async with session.get(json_resp['log_url'][0]) as bbb_response:
                    log.debug('bbb second response header is: %s',
                              bbb_response.headers.get('content-encoding', 'none'))

                    try:
                        test_for_bad_log = await bbb_response.json()
                        if test_for_bad_log['message'] is 'Artifact not found':
                            log.debug('Artifact not found at %s', url)
                            return None
                    except JSONDecodeError:
                        pass

                    return await bbb_response.text()

            except JSONDecodeError:
                log.exception('JSONDecodeError thrown when converting buildbot-bridge properties to json.')
                return None

            except KeyError as e:
                raise NoLogsExistError(
                    "Missing key 'log_url' in json response for buildbot-bridge. URL used: {}".format(url)
                )
