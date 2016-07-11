import logging
import os

from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)


class BasePlugin(object):

    S3_KEY_TEMPLATE = '{}_run{}_log'
    LOG_TEMPLATES = {
        'buildbot-bridge': 'https://queue.taskcluster.net/v1/task/{task_id}/runs/{run_id}/artifacts/public/properties.json',
        'aws-provisioner-v1': 'https://queue.taskcluster.net/v1/task/{task_id}/runs/{run_id}/artifacts/public/logs/live.log',
    }

    def __init__(self):
        log.info('%s plugin initialized', self.name)

    @property
    def name(self):
        return self.__module__.split('.')[-1]

    def task_info(self, config_section):
        return config_section['subject'], config_section['message']

    def get_logs_urls(self, task, task_id, runs):
        if 'log_collect' in os.environ['PN_SERVICES'].split(':') and task['provisionerId'] in self.LOG_TEMPLATES:
            return ['https://{}.s3.amazonaws.com/{}'.format(os.environ['S3_BUCKET'], self.S3_KEY_TEMPLATE.format(task_id, run['runId'])) for run in runs]
        else:
            return None

    @async_time_me
    async def notify(self, body, envelope, properties, task, task_id, taskcluster_exchange, exchange_config):
        log.error('Notify not implemented for %s', self.name)
        return None


class AWSPlugin(BasePlugin):
    def __init__(self):
        self.access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        self.secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        log.info('%s plugin initialized', self.name)
