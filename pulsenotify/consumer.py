import json
import logging
from importlib import import_module

from pulsenotify.util import fetch_task

log = logging.getLogger(__name__)

EXCHANGES = [
#     "exchange/taskcluster-queue/v1/task-defined",
#     "exchange/taskcluster-queue/v1/task-pending",
#     "exchange/taskcluster-queue/v1/task-running",
#     "exchange/taskcluster-queue/v1/artifact-created",
    "exchange/taskcluster-queue/v1/task-completed",
    "exchange/taskcluster-queue/v1/task-failed",
    "exchange/taskcluster-queue/v1/task-exception",
]


class NotifyConsumer(object):
    #routing_key = 'route.connor'
    routing_key = 'route.index.releases.v1.#'

    def __init__(self, services_list):
        self.service_objects = [import_module('pulsenotify.plugins.' + service).Plugin()
                                for service in services_list]
        self.test_sent = 0
        log.info('Consumer initialized.')

    @property
    def exchanges(self):
        return EXCHANGES

    async def dispatch(self, channel, body, envelope, properties):
        log.info('Dispatch called.')
        taskcluster_exchange = envelope.exchange_name.split('/')[-1]
        body = json.loads(body.decode("utf-8"))
        task_id = body["status"]["taskId"]
        task = await fetch_task(task_id)

        try:
            enabled_plugins = task['extra']['notification'][taskcluster_exchange]
            for service in filter(lambda obj: obj.name in enabled_plugins, self.service_objects):
                try:
                    await service.notify(channel, body, envelope, properties, task, taskcluster_exchange)
                except Exception:
                    log.exception("Service %s failed to notify for task %s.", service.name, task_id)

        except KeyError as ke:
            log.debug("Task %s has no notifications for %s", task_id, taskcluster_exchange)
        finally:
            log.info('Acknowledging consumption of task %s', task_id)
            return await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)
