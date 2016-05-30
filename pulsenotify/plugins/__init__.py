import logging
import os

log = logging.getLogger(__name__)


class BasePlugin(object):
    def __init__(self):
        log('%s plugin initialized', self.name)

    @property
    def name(self):
        return self.__module__.split('.')[-1]

    def task_info(self, body, task, taskcluster_exchange):
        return (task['extra']['notification'][taskcluster_exchange][self.name],
                body["status"]["taskId"],)

    def get_logs_urls(self, task_id, runs):
        return ['https://{}.s3.amazonaws.com/{}_run{}_log'.format(os.environ['S3_BUCKET'], task_id, run['runId']) for run in runs]

    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        log.error('Notify not implemented for %s', self.name)
        return None


class AWSPlugin(BasePlugin):
    def __init__(self):
        self.access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        self.secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        log.info('%s plugin initialized', self.name)
