import logging
import aiohttp
import gzip
import boto3
from . import AWSPlugin

log = logging.getLogger(__name__)


class Plugin(AWSPlugin):
    """
    Compression details:
    https://docs.python.org/3.5/library/archiving.html
    """
    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        task_config, task_id = self.task_info(body, task, taskcluster_exchange)

        for run in body['status']['runs']:
            try:
                artifact = await self.get_artifact(task_id, run['runId'])
                #artifact_gzip = gzip.compress(artifact)
                """
                client = boto3.client('s3',
                                        aws_access_key_id = self.access_key_id,
                                        aws_secret_access_key = self.secret_access_key)

                response = client.put_object(  # TODO: fix this call to actually work (remove/fix kwargs)
                    ACL='private' | 'public-read' | 'public-read-write' | 'authenticated-read' | 'aws-exec-read' | 'bucket-owner-read' | 'bucket-owner-full-control',
                    Body=artifact_gzip,
                    Bucket='string',
                    CacheControl='string',
                    ContentDisposition='string',
                    ContentEncoding='gzip',
                    ContentLanguage='string',
                    ContentLength=123,
                    ContentMD5='string',
                    ContentType='text/plain',
                    Expires=datetime(2015, 1, 1),
                    GrantFullControl='string',
                    GrantRead='string',
                    GrantReadACP='string',
                    GrantWriteACP='string',
                    Key='string',
                    Metadata={
                        'string': 'string'
                    },
                    ServerSideEncryption='AES256' | 'aws:kms',
                    StorageClass='STANDARD' | 'REDUCED_REDUNDANCY' | 'STANDARD_IA',
                    WebsiteRedirectLocation='string',
                    SSECustomerAlgorithm='string',
                    SSECustomerKey='string',
                    SSEKMSKeyId='string',
                    RequestPayer='requester'
                )
                """
                # async with aiohttp.Timeout(10), aiohttp.ClientSession(headers=self.header) as session:
                #     async with session.post(task_config['post_url'], data=artifact_gzip) as response:
                #         if response.status == 200:
                #             log.info('Log for task %s, run %s posted to %s', task_id, run['runId'], task_config['url'])
                #         else:
                #             log.debug('%s: Bad exit code (%s) for task %s run %s', self.name, response.status, task_id, run['runId'])

            except KeyError as ke:
                log.error('%s: No artifacts or no runId for %s - %s', self.name, task_id, ke)

    async def get_artifact(self, task_id, run_number):
        url = "https://queue.taskcluster.net/v1/task/{}/runs/{}/artifacts/public/logs/live.log".format(task_id, run_number)
        with aiohttp.Timeout(10), aiohttp.ClientSession() as session:
            response = await session.get(url)
            return await response.text()

    @property
    def header(self):
        return {
            'Content-Type': 'text/plain',
            'Content-Encoding': 'gzip'
        }
