import json
import logging

import boto3

from blessings import Terminal
from pulsenotify.util import task_term_info, fetch_task

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

    def __init__(self, notify_config):
        self.access_key_id = notify_config['aws_access_key_id']
        self.secret_access_key = notify_config['aws_secret_access_key']
        self.test_sent = 0

    def get_exchanges(self):
        #return EXCHANGES
        return ["exchange/taskcluster-queue/v1/task-defined"]  # For testing only

    async def dispatch(self, channel, body, envelope, properties):
        exchange = envelope.exchange_name.split('/')[-1]
        print(exchange + '\n')
        log.debug("Decoding body: %r", body)

        body = json.loads(body.decode("utf-8"))
        try:
            await self.handle(channel, body, envelope, properties, exchange)
        except:
            log.exception("Failed to handle")
        finally:
            return await channel.basic_client_ack(
                 delivery_tag=envelope.delivery_tag)


    async def handle(self, channel, body, envelope, properties, exchange):
        task = await fetch_task(body["status"]["taskId"])
        print(task)
        try:
            extra = task['extra']
            print(extra)
            notify_info = extra['notification']
            print(notify_info)

            arn = notify_info[exchange]['arn']
            message = notify_info[exchange]['message']
        except KeyError:
            log.debug('[!] No notification/exchange section in task %s' % body['status']['taskId'])

        await self.notify(arn, message)
        return


    async def notify(self, arn, message):
        """Perform the notification (ie email relevant addresses)"""
        client = boto3.client('sns', aws_access_key_id=self.access_key_id,
                              aws_secret_access_key=self.secret_access_key)

        resp = client.publish(TopicArn=arn, Message=message)
        print('[!] Notified!')
