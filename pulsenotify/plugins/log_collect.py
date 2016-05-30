import logging
import aiohttp
import gzip
import boto3
from . import AWSPlugin

log = logging.getLogger(__name__)

PUBLIC_LOG_URL = "https://queue.taskcluster.net/v1/task/{}/runs/{}/artifacts/public/logs/live.log"
S3_KEY_TEMPLATE = '{}_run{}_log'
HEADER = dict(ACL='public-read',
              ContentType='text/plain',
              ContentEncoding='gzip')


class Plugin(AWSPlugin):
    """
    Compression details:
    https://docs.python.org/3.5/library/archiving.html
    """
    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        task_config, task_id = self.task_info(body, task, taskcluster_exchange)

        s3 = boto3.resource('s3',   aws_access_key_id=self.access_key_id,
                                    aws_secret_access_key=self.secret_access_key)
        log_bucket = s3.Bucket('sheehan-test')

        for run in body['status']['runs']:
            try:
                s3_key = S3_KEY_TEMPLATE.format(task_id, run['runId'])
                artifact = await self.get_artifact(task_id, run['runId'])
                artifact_gzip = gzip.compress(bytes(artifact, 'utf-8'))

                log_bucket.put_object(Body=artifact_gzip,
                                      Key=s3_key,
                                      **HEADER)

                log.info('%s: log for task %s run %s uploaded to s3.', self.name, task_id, run['runId'])
            except KeyError as ke:
                log.error('%s: No artifacts or no runId for %s - %s', self.name, task_id, ke)

    async def get_artifact(self, task_id, run_number):
        url = PUBLIC_LOG_URL.format(task_id, run_number)
        with aiohttp.Timeout(10), aiohttp.ClientSession() as session:
            response = await session.get(url)
            return await response.text()