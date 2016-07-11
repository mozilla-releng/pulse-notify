import logging
import gzip
import os
from json import JSONDecodeError

import aiohttp
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
    async def notify(self, body, envelope, properties, task, task_id, taskcluster_exchange, exchange_config):
        s3 = boto3.resource('s3', aws_access_key_id=self.access_key_id, aws_secret_access_key=self.secret_access_key)
        log_bucket = s3.Bucket(self.s3_bucket)

        provisioner_id = task['provisionerId']
        if provisioner_id not in self.LOG_TEMPLATES:
            log.debug('ProvisionerId %s not valid for log upload.', provisioner_id)
            return  # Exit if the provisionerId doesn't match a known pattern

        for run in body['status']['runs']:
            try:
                run_id = run['runId']
                log_url = self.LOG_TEMPLATES[provisioner_id].format(task_id=task_id, run_id=run_id)
                s3_key = self.S3_KEY_TEMPLATE.format(task_id, run_id)
                task_log = await get_log(log_url, provisioner_id)

                if task_log is None:
                    log.debug('Artifact is none.')
                    continue
                else:
                    log.debug('Compressing artifact.')
                    try:
                        if type(task_log) is str:
                            log.debug('artifact is str, converting')
                            task_log = bytes(task_log, 'utf-8')
                        else:
                            log.debug('artifact was bytes')

                        artifact_gzip = gzip.compress(task_log)
                    except TypeError as te:
                        log.exception('TypeError: %s', te)

                log_bucket.put_object(Body=artifact_gzip, Key=s3_key, **HEADER)

                log.info('%s: log for task %s run %s status %s uploaded to s3.', self.name, task_id, run['runId'], taskcluster_exchange)
            except KeyError as ke:
                log.error('%s: No artifacts or no runId for %s - %s', self.name, task_id, ke)


async def get_log(url, provisioner_id):
    with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if provisioner_id == 'buildbot-bridge':
                log.debug('bbb response header is: %s', response.headers.get('content-encoding', 'none'))
                try:
                    json_resp = await response.json()
                    log.debug('bbb actual log filename: %s', json_resp['log_url'][0])
                    async with session.get(json_resp['log_url'][0]) as bbb_response:
                        log.debug('bbb second response header is: %s', bbb_response.headers.get('content-encoding', 'none'))
                        return await bbb_response.text()

                except JSONDecodeError:
                    log.exception('JSONDecodeError thrown when converting buildbot-bridge properties to json.')
                    return None

                except KeyError:
                    log.exception('No key \'log_url\' in json response for buildbot-bridge')
                    return None

            elif provisioner_id == 'aws-provisioner-v1':
                log.debug('aws response header is: %s', response.headers.get('content-encoding', 'none'))
                return await response.text()

            else:
                log.debug('Unknown provisionerId %s given to get_log', provisioner_id)
                return None
