import json
import logging
import smtplib

from smtplib import SMTPConnectError

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


class BaseConsumer(object):
    routing_key = '#'
    t = Terminal()

    def __init__(self, nc):
        self.email = nc['notify_email']
        self.passwd = nc['notify_pass']
        self.host = nc['notify_host']
        self.port = nc['notify_port']
        self.test_sent = 0

    def get_exchanges(self):
        #return EXCHANGES
        return ["exchange/taskcluster-queue/v1/task-completed"]  # For testing only

    async def dispatch(self, channel, body, envelope, properties):
        exchange = envelope.exchange_name
        #log.debug("Decoding body: %r", body)

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
        info = await task_term_info(body)
        print(self.t.green("[COMPLETE]"), info)
        await self.notify(['csheehan@mozilla.com'], info)
        return

    async def handle_task_failed(self, channel, body, envelope, properties):
        pass

    async def handle_task_exception(self, channel, body, envelope, properties):
        pass

    async def handle_unknown(self, channel, body, envelope, properties):
        pass

    async def notify(self, recipients, subject):
        """Perform the notification (ie email relevant addresses)"""
        # TODO: fill in the steps with the necessary information
        if self.test_sent > 5:
            return

        email_message = MIMEMultipart()
        email_message['Subject'] = subject
        email_message['To'] = ', '.join(recipients)

        email_body = MIMEText('placeholder_body')
        email_message.attach(email_body)

        try:
            s = smtplib.SMTP(self.host, self.port)
            s.ehlo()
            s.starttls()
            s.login(self.email, self.passwd)
            s.sendmail(self.email, recipients, email_message.as_string())
            s.quit()
            print(self.t.green("[NOTIFIED]"), "CHECK UR EMAIL, bottom of notify reached without breaking")
            self.test_sent += 1
        except SMTPConnectError as ce:
            print('[!] SMTPConnectError: ' + ce.message)



class ReleaseConsumer(BaseConsumer):
    routing_key = 'route.index.releases.v1.#'
    t = Terminal()

    def get_exchanges(self):
        exchanges = super().get_exchanges()
        ignore_suffixes = [
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
