import os
import logging
from . import BasePlugin

from bottom import Client

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
        - IRC_PASS
    """

    def __init__(self, loop=None):
        #  Create the client and add all functions with 'on' decorator as event handlers for
        #  different irc message types
        self.irc_client = Client(host=os.environ['IRC_HOST'],
                                 port=os.environ['IRC_PORT'],
                                 ssl=True, loop=loop)

        @self.irc_client.on('CLIENT_CONNECT')
        def connect(**kwargs):
            self.irc_client.send('NICK', nick=os.environ['IRC_NICK'])
            self.irc_client.send('USER', user=os.environ['IRC_NAME'], realname=os.environ['IRC_NAME'])
            self.irc_client.send('PASS', password=os.environ['IRC_PASS'])

        @self.irc_client.on('CLIENT_DISCONNECT')
        async def reconnect(**kwargs):
            #  If the client disconnects, try and reconnect
            log.debug('Disconnect registered, reconnecting...')
            try:
                await self.irc_client.connect()
            except ConnectionRefusedError:
                log.exception('IRC reconnection refused.')

        @self.irc_client.on('PING')
        def keep_alive(message, **kwargs):
            #  Reply to a 'ping' message with a 'pong'
            self.irc_client.send('PONG', message=message)

        @self.irc_client.on(NOTIFY_SIGNAL_NAME)
        async def irc_notify(task_id=None, status=None, logs=None, channel=None, message=None, **kwargs):
            #  Send a notification message to a channel
            self.irc_client.send('JOIN', channel=channel)
            task_message = '{task_id}: {message}'.format(task_id=task_id, message=message)
            self.irc_client.send('privmsg', target=channel, message=irc_format(task_message, status))

            #  Send the log links, tabbed out
            if logs is not None:
                for log_link in logs:
                    self.irc_client.send('privmsg',
                                         target=channel,
                                         message=irc_format('\t\t' + log_link['destination_url'], status))

        self.irc_client.loop.create_task(self.irc_client.connect())

        log.info('{} plugin initialized.'.format(self.name))

    async def notify(self, task_data, status_config):
        if 'channels' not in status_config:
            log.debug('No IRC channels specified in task %r notification config.', task_data)
            return

        for chan in status_config['channels']:
            try:
                self.irc_client.trigger(NOTIFY_SIGNAL_NAME, status=task_data.status, channel=chan,
                                        message=status_config['message'], logs=task_data.log_data(),
                                        task_id=task_data.id)
            except TypeError as te:
                log.exception('TypeError: %s', te)

        log.info('Notified with IRC for %s', task_data)
