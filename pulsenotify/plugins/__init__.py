import logging
import os

from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)


class BasePlugin(object):

    S3_KEY_TEMPLATE = '{branch}/{product}-{version}/build{build_number}/{name}-{platform}-{task_id}-{run_id}'
    LOG_TEMPLATES = {
        'buildbot-bridge': 'https://queue.taskcluster.net/v1/task/{task_id}/runs/{run_id}/artifacts/public/properties.json',
        'aws-provisioner-v1': 'https://queue.taskcluster.net/v1/task/{task_id}/runs/{run_id}/artifacts/public/logs/live.log',
    }

    def __init__(self):
        log.info('%s plugin initialized', self.name)

    @property
    def name(self):
        return self.__module__.split('.')[-1]

    def task_info(self, config_section):  # TODO: remove, no longer needed
        return config_section['subject'], config_section['message']

    def make_s3_key(self, task, task_id, run_id):
        try:
            build_properties = task['extra']['build_props']
            task_metadata = task['metadata']
            platform = build_properties.get('platform', 'all')

            if not platform:
                platform = 'all'

            name = task_metadata['name'].replace('/', '_').replace('\\', '_')

            s3_key = self.S3_KEY_TEMPLATE.format(branch=build_properties['branch'],
                                              product=build_properties['product'],
                                              version=build_properties['version'],
                                              build_number=build_properties['build_number'],
                                              name=name,
                                              platform=platform,
                                              task_id=task_id,
                                              run_id=run_id)

            s3_key = s3_key.replace(' ', '_')

            return s3_key

        except KeyError:
            log.exception('Could not create s3 key for task %s, logs not uploaded', task_id)

    def get_logs_urls(self, task, task_id, runs):
        if 'log_collect' in os.environ['PN_SERVICES'].split(':') and task['provisionerId'] in self.LOG_TEMPLATES:
            #  Fill in the s3 key template without the runId
            s3_key_empty_run_id = self.make_s3_key(task, task_id, '{run_id}')

            #  Return list of above key with runId filled in
            return ['https://{bucket}.s3.amazonaws.com/{log_key}'
                        .format(bucket=os.environ['S3_BUCKET'],
                                log_key=s3_key_empty_run_id.format(run_id=run['runId']))
                    for run in runs]

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
