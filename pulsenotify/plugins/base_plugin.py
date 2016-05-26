import logging

log = logging.getLogger(__name__)


class BasePlugin(object):

    @property
    def name(self):
        return self.__module__.split('.')[-1]

    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        log.error('Notify not implemented for %s', self.name)
        return None

    def get_notify_section(self, task, taskcluster_exchange):
        return task['extra']['notification'][taskcluster_exchange][self.name]
