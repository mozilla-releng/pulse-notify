import logging
import gzip
import os
import boto3
from . import AWSPlugin
from pulsenotify.util import async_time_me

log = logging.getLogger(__name__)


HEADER = {
    'ACL': 'public-read',
    'ContentType': 'text/plain',
    'ContentEncoding': 'gzip',
}


class Plugin(AWSPlugin):

    def __init__(self):
        super(Plugin, self).__init__()
        self.s3_bucket = os.environ['S3_BUCKET']

    @async_time_me
    async def notify(self, task_data, exchange_config):
        log.debug('log_collect called for %r', task_data)
        log_data = task_data.log_data()
        if not log_data:
            log.debug('No logs for %r', task_data)
            return

        s3 = boto3.resource('s3', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.secret_access_key)
        log_bucket = s3.Bucket(self.s3_bucket)

        for run_log in log_data:
            #  Use gzip compression on log
            log.debug('Compressing artifact.')
            try:
                if type(run_log['data']) is str:
                    log.debug('Artifact with key %s is str, converting', run_log['s3_key'])
                    task_log = bytes(run_log['data'], 'utf-8')
                else:
                    task_log = run_log['data']

                log_gzip = gzip.compress(task_log)
            except TypeError as te:
                log.exception('TypeError: %s', te)

            #  Upload log to S3 bucket
            log_bucket.put_object(Body=log_gzip, Key=run_log['s3_key'], **HEADER)

            log.info('%s: log for %r uploaded to Amazon S3', self.name, task_data)
