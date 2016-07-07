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
            except ConnectionRefusedError:
                log.exception('IRC reconnection refused.')

        @self.irc_client.on('PING')
        def keep_alive(message, **kwargs):
            self.irc_client.send('PONG', message=message)

        @self.irc_client.on(NOTIFY_SIGNAL_NAME)
        async def irc_notify(task_id=None, exch=None, logs=None, channel=None, message=None, **kwargs):
            self.irc_client.send('JOIN', channel=channel)
            task_message = '{task_id}: {message}'.format(task_id=task_id, message=message)
            if logs is not None:
                task_message += ' Logs: ({log_sep})'.format(log_sep=logs)
            self.irc_client.send('privmsg', target=channel, message=irc_format(task_message, exch))

        self.irc_client.loop.create_task(self.irc_client.connect())

        log.info('{} plugin initialized.'.format(self.name))

    async def notify(self, body, envelope, properties, task, task_id, taskcluster_exchange, exchange_config):
        log_urls = self.get_logs_urls(task_id, body['status']['runs'])
        logs = ', '.join(log_urls) if type(log_urls) is list else None

        try:
            for chan in exchange_config['channels']:
                try:
                    self.irc_client.trigger(NOTIFY_SIGNAL_NAME, exch=taskcluster_exchange, channel=chan,
                                                  message=exchange_config['message'], logs=logs, task_id=task_id)
                except TypeError as te:
                    log.exception('TypeError: %s', te)
        except KeyError:
            log.debug('No channels specified in exchange config.')

        log.info('Notified with IRC for task %s' % task_id)
