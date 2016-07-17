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


class NotifyConsumer(object):

    def __init__(self, env):
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
        self.identities = safe_load(open(os.path.curdir + '/pulsenotify/id_configs/' + env + '.yml', 'r'))

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
            log.info('Dispatch called.')
            taskcluster_exchange = envelope.exchange_name.split('/')[-1]
            body = json.loads(body.decode("utf-8"))

            task_id = body["status"]["taskId"]

            #  Fetch task, retrying a few times in case of a timeout
            for attempt in range(1, 6):
                full_task = await fetch_task(task_id)
                if full_task:
                    break
                else:
                    log.debug('Task definition fetch attempt %s failed, retrying...', attempt)
            else:
                log.warn('Task definition fetch failed for task %s', task_id)

            original_configuration = full_task['extra']['notifications'][taskcluster_exchange]

            notify_sections = self.generate_notification_configurations(original_configuration)

            for id_name, id_section in notify_sections.items():
                try:
                    enabled_plugins = id_section['plugins']
                    for plugin_name in enabled_plugins:
                        try:
                            await self.notifiers[plugin_name].notify(body, envelope, properties,  # AMQP Info
                                                                     full_task, task_id, taskcluster_exchange, id_section)  # Taskcluster/Notification
                        except KeyError:
                            log.exception("Plugin lookup failed for %s, task %s and id %s", plugin_name, task_id, id_name)
                except KeyError as e:
                    log.debug('Plugins section missing from %s notification configuration', id_name)
        except KeyError as ke:
            log.debug('KeyError raised trying to notify for task %s with bad key %s', task_id, ke)
        except TypeError as te:
            log.debug('TypeError %s', te)
            log.debug('%s has \'no notifications\' in notifications section.', task_id)
        finally:
            log.info('Acknowledging consumption of task %s', task_id)
            return await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)

    def generate_notification_configurations(self, original_configuration):
        #  This function creates the mapping of identities to the corresponding notification configurations for a
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
