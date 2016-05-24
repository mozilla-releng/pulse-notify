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
        return 'sns'

    async def notify(self, task_config):
        """Perform the notification (ie email relevant addresses)"""
        for i in range(5):
            try:
                client = boto3.client('sns',
                                      aws_access_key_id=self.access_key_id,
                                      aws_secret_access_key=self.secret_access_key)

                client.publish(TopicArn=task_config['arn'], Message=task_config['message'])
                log.info('[!] Notified with SNS!')
                return
            except Boto3Error as b3e:
                log.exception('[!] Attempt %s: Boto3Error %s', str(i), b3e.message)
        else:
            log.exception('[!] Could not notify %s via SNS', task_config['arn'])
