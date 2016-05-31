import os
import logging
from . import BasePlugin

from bottom import Client

log = logging.getLogger(__name__)


class Plugin(BasePlugin):
    """
    Internet Relay Chat Plugin for the Pulse Notification system
    TODO: implement!
    """

    def __init__(self):
        self.irc_client = Client(host=os.environ['IRC_HOST'],
                                 port=os.environ['IRC_PORT'],
                                 ssl=False)

        @self.irc_client.on('CLIENT_CONNECT')
        def connect(**kwargs):
            self.irc_client.send('NICK', nick=os.environ['IRC_NICK'])
            self.irc_client.send('USER', user=os.environ['IRC_NICK'], realname='PULSE-NOTIFY-IRC-PLUGIN')
            self.irc_client.send('JOIN', channel='#testchan')

        @self.irc_client.on('CLIENT_DISCONNECT')
        async def reconnect(**kwargs):
            log.debug('Disconnect registered, reconnecting...')
            try:
                await self.irc_client.connect()
            except ConnectionRefusedError as cre:
                log.exception('Connection refused.')

        @self.irc_client.on('PING')
        def keepalive(message, **kwargs):
            self.irc_client.send('PONG', message=message)

        @self.irc_client.on('PRIVMSG')
        async def irc_notify(task_id=None, exch=None, **kwargs):
            self.irc_client.send('privmsg', target='#testchan', message='Task {} has achieved status {}'.format(task_id, exch))

        self.irc_client.loop.create_task(self.irc_client.connect())
        log.info('{} plugin initialized.'.format(self.name))

    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        task_config, task_id = self.task_info(body, task, taskcluster_exchange)
        self.irc_client.trigger('PRIVMSG', task_id=task_id, exch=taskcluster_exchange)
        log.info('Notified with IRC for task %s' % task_id)
