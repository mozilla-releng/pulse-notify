import logging
import os

from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)


class BasePlugin(object):

    def __init__(self):
        log.info('%s plugin initialized', self.name)

    @property
    def name(self):
        return self.__module__.split('.')[-1]

    @async_time_me
    async def notify(self, task_data, exchange_config):
        log.error('Notify not implemented for %s', self.name)
        return None


class AWSPlugin(BasePlugin):
    def __init__(self):
        self.access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        self.secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        log.info('%s plugin initialized', self.name)
