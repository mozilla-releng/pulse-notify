import os
import logging
from . import BasePlugin
from asyncirc import irc

log = logging.getLogger(__name__)


class Plugin(BasePlugin):
    """
    Internet Relay Chat Plugin for the Pulse Notification system
    TODO: implement!
    """
    def __init__(self):
        self.connection = irc.connect(os.environ['IRC_HOST'], os.environ['IRC_PORT'], use_ssl=True)
        self.connection.register(os.environ['IRC_NICK'], os.environ['IRC_IDENT'], os.environ['IRC_REALNAME'])

    def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        log.error('Notify not yet implemented in %s' % self.name)
        return
