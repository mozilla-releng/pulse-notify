import json
import logging
import os
from importlib import import_module
from yaml import safe_load

from pulsenotify.util import fetch_task
from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)

EXCHANGES = {
    # "exchange/taskcluster-queue/v1/task-defined",
    # "exchange/taskcluster-queue/v1/task-pending",
    # "exchange/taskcluster-queue/v1/task-running",
    "exchange/taskcluster-queue/v1/artifact-created",
    "exchange/taskcluster-queue/v1/task-completed",
    "exchange/taskcluster-queue/v1/task-failed",
    "exchange/taskcluster-queue/v1/task-exception",
}

ROUTING_KEYS = {
    'route.connor',
    'route.index.releases.v1.#',
}


class NotificationsNotConfiguredError(Exception):
    pass


class StatusNotificationsNotConfiguredError(Exception):
    pass


class NoNotificationsSpecifiedError(Exception):
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
            except ImportError:
                log.exception('No plugin named %s, initialization failed', service)

        #  Identities contain information about how to notify a single group/person/'identity'.
        #  The identities are pulled in from a yaml file. If an identity is present in the 'ids' section of a
        #  notification configuration, the information for that id will add and overwrite the initial configuration.
        self.identities = safe_load(open(os.path.curdir + '/pulsenotify/id_configs/' + os.environ['ID_ENV'] + '.yml', 'r'))

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
        try:
            body = json.loads(body.decode("utf-8"))
            task_id = body["status"]["taskId"]
            task_status = envelope.exchange_name.split('/')[-1]

            log.info('Processing notifications for task %s, status %s', task_id, task_status)


            #  Fetch task, retrying a few times in case of a timeout
            for attempt in range(1, 6):
                full_task = await fetch_task(task_id)
                if full_task:
                    break
                else:
                    log.debug('Task definition fetch attempt %s failed, retrying...', attempt)
            else:
                log.warn('Task definition fetch failed for task %s', task_id)
                return

            notify_sections = self.generate_notification_configurations(full_task, task_status)

            for id_name, id_section in notify_sections.items():
                if 'plugins' in id_section:
                    enabled_plugins = id_section['plugins']
                else:
                    log.debug('No plugins section found for taskId %s with status %s, for id %s',
                              task_id, task_status, id_name)
                    continue

                for plugin_name in enabled_plugins:
                    if plugin_name in self.notifiers:
                        await self.notifiers[plugin_name].notify(body, envelope, properties,  # AMQP Info
                                                                 full_task, task_id, task_status, id_section)  # Taskcluster/Notification
                    else:
                        log.warn('No plugin object %s for task %s found in consumer.notifiers', plugin_name, task_id)

        except NotificationsNotConfiguredError:
            log.exception('Task %s has no notifications section.', task_id)

        except NoNotificationsSpecifiedError:
            log.exception('Task %s has a notifications section, but no notification configurations', task_id)

        except StatusNotificationsNotConfiguredError:
            log.exception('Task %s has no notification configuration for status %s', task_id, task_status)

        except Exception as e:
            log.exception('Exception %s caught by generic exception trap', e)

        finally:
            log.info('Acknowledging consumption of task %s', task_id)
            return await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)

    def generate_notification_configurations(self, full_task, task_status):
        #  Retrieve the notifications section out of the task
        try:
            notification_section = full_task['extra']['notifications']
        except KeyError:
            raise NotificationsNotConfiguredError()

        #  Retrieve the notification configuration for this task status
        try:
            original_configuration = notification_section[task_status]
        except KeyError:
            raise StatusNotificationsNotConfiguredError()
        except TypeError:
            raise NoNotificationsSpecifiedError()

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
