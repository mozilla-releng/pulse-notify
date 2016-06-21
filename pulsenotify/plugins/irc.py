import os
import logging
from . import BasePlugin

from bottom import Client
from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)

IRC_CODES = {
    'BOLD': '\u0002',
    'ITALIC': '\35',
    'UNDERLINE': '\37',
    'RED': '\u000304',
    'GREEN': '\u000303',
    'BLUE': '\u000302',
    'PURPLE': '\u000306',
}

COLOUR_MAP = {
    'task-completed': 'GREEN',
    'task-failed': 'RED',
    'artifact-created': 'BLUE',
    'task-exception': 'PURPLE',
}

NOTIFY_SIGNAL_NAME = 'SEND_NOTIFY'


def irc_format(string, fmt_type):
    fmt_type = COLOUR_MAP.get(fmt_type, fmt_type)
    return '{0}{1}{0}'.format(IRC_CODES.get(fmt_type, ''), string)


class Plugin(BasePlugin):
    """
    Internet Relay Chat Plugin for the Pulse Notification system

    The following environment variables must be present for the plugin to function:
        - IRC_HOST
        - IRC_NAME
        - IRC_NICK
        - IRC_PORT
        - IRC_CHAN
        - IRC_PASS

    In each task, under extra/notification/<desired exchange>/plugins/, there must be an object with the following schema:
        - recipients
    """

    def __init__(self):
        self.irc_client = Client(host=os.environ['IRC_HOST'],
                                 port=os.environ['IRC_PORT'],
                                 ssl=True)

        @self.irc_client.on('CLIENT_CONNECT')
        def connect(**kwargs):
            self.irc_client.send('NICK', nick=os.environ['IRC_NICK'])
            self.irc_client.send('USER', user=os.environ['IRC_NAME'], realname=os.environ['IRC_NAME'])
            self.irc_client.send('PASS', password=os.environ['IRC_PASS'])

        @self.irc_client.on('CLIENT_DISCONNECT')
        async def reconnect(**kwargs):
            log.debug('Disconnect registered, reconnecting...')
            try:
                await self.irc_client.connect()
            except ConnectionRefusedError as cre:
                log.exception('Connection refused.')

        @self.irc_client.on('PING')
        def keep_alive(message, **kwargs):
            self.irc_client.send('PONG', message=message)

        @self.irc_client.on(NOTIFY_SIGNAL_NAME)
        @async_time_me
        async def irc_notify(task_id=None, exchange_config=None, subject=None, message=None, logs=None, exch=None, **kwargs):
            if not all(v is not None for v in [task_id, subject, message, exch]):
                log.debug('One of IRC notify kwargs is None!')
            else:

                self.irc_client.send('JOIN', channel=os.environ['IRC_CHAN'])

                try:
                    recipients = ': '.join(exchange_config['nicks']) + ' ' if exchange_config['nicks'] is not None \
                        else ''
                except TypeError as te:
                    recipients = ''
                    log.debug('IRC config TypeError')

                task_message = '{recip}{task_id} {subject}: {message}.'.format(
                    recip=irc_format(recipients, 'ITALIC'),
                    task_id=irc_format(irc_format(task_id, 'BOLD'), 'UNDERLINE'),
                    message=message,
                    subject=irc_format(subject, 'BOLD'))

                if logs is not None:
                    task_message += ' Logs: ({log_sep})'.format(log_sep=logs)

                self.irc_client.send('privmsg', target=os.environ['IRC_CHAN'], message=irc_format(task_message, exch))

        self.irc_client.loop.create_task(self.irc_client.connect())
        log.info('{} plugin initialized.'.format(self.name))

    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        subject, message, exchange_config, task_id = self.task_info(body, task, taskcluster_exchange)

        log_urls = self.get_logs_urls(task_id, body['status']['runs'])
        logs = ', '.join(log_urls) if type(log_urls) is list else None

        self.irc_client.trigger(NOTIFY_SIGNAL_NAME,
                                task_id=task_id,
                                config=exchange_config,
                                message=message,
                                subject=subject,
                                logs=logs,
                                exch=taskcluster_exchange)
        log.info('Notified with IRC for task %s' % task_id)
