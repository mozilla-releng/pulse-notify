import json
import logging
import asyncio

from blessings import Terminal

from pulsenotify.util import task_term_info

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


class BaseConsumer(object):
    routing_key = '#'

    def get_exchanges(self):
        return EXCHANGES

    async def dispatch(self, channel, body, envelope, properties):
        exchange = envelope.exchange_name
        log.debug("Decoding body: %r", body)
        body = json.loads(body.decode("utf-8"))
        try:

            if exchange.endswith("task-defined"):
                await self.handle_task_defined(channel, body, envelope, properties)
            elif exchange.endswith("task-pending"):
                await self.handle_task_pending(channel, body, envelope, properties)
            elif exchange.endswith("task-running"):
                await self.handle_task_running(channel, body, envelope, properties)
            elif exchange.endswith("task-completed"):
                await self.handle_task_completed(channel, body, envelope, properties)
            elif exchange.endswith("task-failed"):
                await self.handle_task_failed(channel, body, envelope, properties)
            elif exchange.endswith("task-exception"):
                await self.handle_task_exception(channel, body, envelope, properties)
            elif exchange.endswith("artifact-created"):
                await self.handle_artifact_created(channel, body, envelope, properties)
            else:
                await self.handle_unknown(body)
        except:
            log.exception("Failed to handle")
        finally:
            return await channel.basic_client_ack(
                 delivery_tag=envelope.delivery_tag)

    async def handle_task_defined(self, channel, body, envelope, properties):
        pass

    async def handle_task_pending(self, channel, body, envelope, properties):
        pass

    async def handle_task_running(self, channel, body, envelope, properties):
        pass

    async def handle_artifact_created(self, channel, body, envelope, properties):
        pass

    async def handle_task_completed(self, channel, body, envelope, properties):
        pass

    async def handle_task_failed(self, channel, body, envelope, properties):
        pass

    async def handle_task_exception(self, channel, body, envelope, properties):
        pass

    async def handle_unknown(self, channel, body, envelope, properties):
        pass


class ReleaseConsumer(BaseConsumer):
    routing_key = 'route.index.releases.v1.#'
    t = Terminal()

    def get_exchanges(self):
        exchanges = super().get_exchanges()
        ignore_suffixes =[
            "task-defined",
            "task-pending",
            "task-running",
            "artifact-created"
        ]
        return [e for e in exchanges
                if not any([e.endswith(s) for s in ignore_suffixes])]

    async def handle_task_completed(self, channel, body, envelope, properties):
        info = await task_term_info(body)
        print(self.t.green("[COMPLETE]"), info)

    async def handle_task_failed(self, channel, body, envelope, properties):
        info = await task_term_info(body)
        print(self.t.red("[FAILED]"), info)

    async def handle_task_exception(self, channel, body, envelope, properties):
        info = await task_term_info(body)
        print(self.t.yellow("[EXCEPTION]"), info)

    async def handle_unknown(self, channel, body, envelope, properties):
        info = await task_term_info(body)
        print(self.t.magenta("[SKIP]"), envelope.exchange_name,  info)

    handle_task_defined = handle_task_pending = handle_task_running = \
        handle_artifact_created = handle_unknown
