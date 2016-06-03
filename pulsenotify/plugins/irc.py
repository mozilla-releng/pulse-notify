import os
import logging
from . import BasePlugin

from bottom import Client
from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)


class Plugin(BasePlugin):
    """
    Internet Relay Chat Plugin for the Pulse Notification system
    TODO: implement!
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

        @self.irc_client.on('PRIVMSG')
        async def irc_notify(task_id=None, exch=None, config=None, subject=None, message=None, **kwargs):
            if not all(v is not None for v in [task_id, exch, config, subject, message]):
                log.debug('One of IRC notify kwargs is None!')
            else:
                task_message = '{recip} - Task {task_id} {subject}: {message}'.format(recip=': '.join(config['notify_nicks']),
                                                                    task_id=task_id, message=message, subject=subject)
                self.irc_client.send('privmsg', target=os.environ['IRC_CHAN'], message=task_message)

        self.irc_client.loop.create_task(self.irc_client.connect())
        log.info('{} plugin initialized.'.format(self.name))

    @async_time_me
    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        subject, message, task_config, task_id = self.task_info(body, task, taskcluster_exchange)
        self.irc_client.trigger('PRIVMSG',
                                task_id=task_id,
                                config=task_config,
                                exch=taskcluster_exchange,
                                message=message,
                                subject=subject)
        log.info('Notified with IRC for task %s' % task_id)
