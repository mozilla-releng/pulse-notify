import json
import logging
import os
from importlib import import_module
from yaml import safe_load

from pulsenotify.util import fetch_task
from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)

EXCHANGES = [
    # "exchange/taskcluster-queue/v1/task-defined",
    # "exchange/taskcluster-queue/v1/task-pending",
    # "exchange/taskcluster-queue/v1/task-running",
    "exchange/taskcluster-queue/v1/artifact-created",
    "exchange/taskcluster-queue/v1/task-completed",
    "exchange/taskcluster-queue/v1/task-failed",
    "exchange/taskcluster-queue/v1/task-exception",
]

ROUTING_KEYS = [
    'route.connor',
    'route.index.releases.v1.#',
]


class NotifyConsumer(object):

    def __init__(self):
        services_list = os.environ['PN_SERVICES'].split(':')

        #  notifiers contains objects representing a plugin's method of notification
        self.notifiers = {}
        for service in services_list:
            try:
                self.notifiers[service] = import_module('pulsenotify.plugins.' + service).Plugin()
            except ImportError:
                log.exception('No plugin named %s, initialization failed', service)

        #  identities contains the unique identities that can be specified for notification
        self.identities = safe_load(open(os.path.curdir + '/pulsenotify/id_configs/dev_ids.yml', 'r'))
        self.identities = {**{'default': {}}, **self.identities}  # this line allows for notification without id, straight from task

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
            full_task = await fetch_task(task_id)

            original_section = full_task['extra']['notifications'][taskcluster_exchange]

            notify_sections = {id_name: {**original_section, **id_config}
                               for id_name, id_config in self.identities.items()
                               if id_name in original_section.get('ids', {}) or id_name is 'default'}

            for id_name, id_section in notify_sections.items():
                try:
                    enabled_plugins = id_section['plugins']
                    for plugin_name in enabled_plugins:
                        try:
                            await self.notifiers[plugin_name].notify(body, envelope, properties,  # AMQP Info
                                                                     full_task, task_id, taskcluster_exchange, id_section)  # Taskcluster/Notification
                        except KeyError:
                            log.exception("%s produced a KeyError for task %s and id %s", plugin_name, task_id, id_name)
                except (KeyError, TypeError,):
                    log.debug('Plugins section missing from %s notification section', id_name)
        except KeyError as ke:
            log.debug('%s raised trying to notify for task %s.', ke, task_id)
        except TypeError as te:
            log.debug('TypeError %s', te)
            log.debug('%s has \'no notifications\' in notifications section.', task_id)
        finally:
            log.info('Acknowledging consumption of task %s', task_id)
            return await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)
