import json
import logging
from importlib import import_module

from pulsenotify.util import fetch_task
from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)

EXCHANGES = [
    "exchange/taskcluster-queue/v1/task-defined",
    # "exchange/taskcluster-queue/v1/task-pending",
    # "exchange/taskcluster-queue/v1/task-running",
    # "exchange/taskcluster-queue/v1/artifact-created",
    # "exchange/taskcluster-queue/v1/task-completed",
    # "exchange/taskcluster-queue/v1/task-failed",
    # "exchange/taskcluster-queue/v1/task-exception",
]


class NotifyConsumer(object):
    routing_key = 'route.connor'
    # routing_key = 'route.index.releases.v1.#'

    def __init__(self, services_list):
        self.notifiers = {service: import_module('pulsenotify.plugins.' + service).Plugin() for service in services_list}
        log.info('Consumer initialized.')

    @property
    def exchanges(self):
        return EXCHANGES

    @async_time_me
    async def dispatch(self, channel, body, envelope, properties):
        log.info('Dispatch called.')
        taskcluster_exchange = envelope.exchange_name.split('/')[-1]
        body = json.loads(body.decode("utf-8"))
        task_id = body["status"]["taskId"]
        task = await fetch_task(task_id)

        try:
            enabled_plugins = task['extra']['notification'][taskcluster_exchange]['plugins']
            for plugin_name in enabled_plugins:
                try:
                    await self.notifiers[plugin_name].notify(channel, body, envelope, properties, task, taskcluster_exchange)
                except Exception:
                    log.exception("Service %s failed to notify for task %s.", plugin_name, task_id)
        except KeyError as ke:
            log.debug("Task %s has no notifications for %s", task_id, taskcluster_exchange)
        finally:
            log.info('Acknowledging consumption of task %s', task_id)
            return await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)
