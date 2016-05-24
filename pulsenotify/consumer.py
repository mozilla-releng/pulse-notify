import json
import logging
from importlib import import_module

from blessings import Terminal
from pulsenotify.util import fetch_task

log = logging.getLogger(__name__)

EXCHANGES = [
    "exchange/taskcluster-queue/v1/task-defined",
    "exchange/taskcluster-queue/v1/task-pending",
    "exchange/taskcluster-queue/v1/task-running",
    "exchange/taskcluster-queue/v1/artifact-created",
    "exchange/taskcluster-queue/v1/task-completed",
    "exchange/taskcluster-queue/v1/task-failed",
    "exchange/taskcluster-queue/v1/task-exception",
]


class NotifyConsumer(object):
    routing_key = 'route.connor'
    t = Terminal()

    def __init__(self, services_config):
        self.service_objects = [import_module('pulsenotify.plugins.' + service['name']).Plugin(service['config'])
                                for service in services_config]
        self.test_sent = 0

    def get_exchanges(self):
        #return EXCHANGES
        return ["exchange/taskcluster-queue/v1/task-defined"]  # TODO: Change, for testing only

    async def dispatch(self, channel, body, envelope, properties):
        log.debug('Dispatch called.')
        taskcluster_exchange = envelope.exchange_name.split('/')[-1]

        body = json.loads(body.decode("utf-8"))
        try:
            await self.handle(channel, body, envelope, properties, taskcluster_exchange)
        except:
            log.exception("[!] Failed to handle message from exchange %s", taskcluster_exchange)
        finally:
            return await channel.basic_client_ack(
                 delivery_tag=envelope.delivery_tag)


    async def handle(self, channel, body, envelope, properties, exchange):
        task = await fetch_task(body["status"]["taskId"])
        try:
            extra = task['extra']
            notification_section = extra['notification']
            exchange_section = notification_section[exchange]
        except KeyError:
            log.debug('[!] No notification/exchange section in task %s' % body['status']['taskId'])
            return

        for service in (obj for obj in self.service_objects if obj.name in exchange_section):
            try:
                await service.notify(exchange_section[service.name])
            except Exception:
                log.exception("Service %s failed!", service.name)
        return
