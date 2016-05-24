import boto3
from boto3.exceptions import Boto3Error
import logging

log = logging.getLogger(__name__)


class Plugin(object):

    def __init__(self, config):
        self.access_key_id = config['aws_access_key_id']
        self.secret_access_key = config['aws_secret_access_key']

    @property
    def name(self):
        return 'ses'

    async def notify(self, task_config):
        for attempt in range(5):
            try:
                client = boto3.client(self.name, aws_access_key_id=self.access_key_id,
                                      aws_secret_access_key=self.secret_access_key)

                client.send_email()  # TODO: setup AWS permissions to test
            except Boto3Error as b3e:
                log.exception('[!] SES attempt %s: Boto3Error - %s', str(attempt), b3e)
        else:
            log.exception('[!] Could not notify %s via SES', task_config['arn'])
