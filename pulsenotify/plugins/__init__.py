import logging
import os

log = logging.getLogger(__name__)


class BasePlugin(object):

    S3_KEY_TEMPLATE = '{}_run{}_log'

    def __init__(self):
        log('%s plugin initialized', self.name)

    @property
    def name(self):
        return self.__module__.split('.')[-1]

    def task_info(self, body, task, taskcluster_exchange):
        try:  # Try to get plugin-specific message, use default if none available
            message = task['extra']['notification'][taskcluster_exchange]['plugins'][self.name]['message']
        except (KeyError, TypeError,):
            message = task['extra']['notification'][taskcluster_exchange]['message']

        try:  # Try to get plugin-specific subject, use default if none available
            subject = task['extra']['notification'][taskcluster_exchange]['plugins'][self.name]['subject']
        except (KeyError, TypeError,):
            subject = task['extra']['notification'][taskcluster_exchange]['subject']

        task_id = body["status"]["taskId"]

        message = message.format(task_id=task_id)
        subject = subject.format(task_id=task_id)

        task_config = task['extra']['notification'][taskcluster_exchange]['plugins'][self.name]

        return subject, message, task_config, task_id

    def get_logs_urls(self, task_id, runs):
        if 'log_collect' in os.environ['PN_SERVICES'].split(':'):
            return ['https://{}.s3.amazonaws.com/{}'.format(os.environ['S3_BUCKET'], self.S3_KEY_TEMPLATE.format(task_id, run['runId'])) for run in runs]
        else:
            return None

    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        log.error('Notify not implemented for %s', self.name)
        return None


class AWSPlugin(BasePlugin):
    def __init__(self):
        self.access_key_id = os.environ['AWS_ACCESS_KEY_ID']
        self.secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
        log.info('%s plugin initialized', self.name)
