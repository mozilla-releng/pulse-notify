from . import AWSPlugin
import boto3
from boto3.exceptions import Boto3Error
import logging
import os

log = logging.getLogger(__name__)


class Plugin(AWSPlugin):
    """
    Amazon SNS Plugin for the Pulse Notification system

    The following environment variables must be present for the plugin to function:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY

    In each task, under extra/<desired exchange>, there must be an object with the following schema:
        - arn (Amazon resource number of SNS topic to deliver notification to)
        - message (body of the notification message)
    """
    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        """Perform the notification (ie email relevant addresses)"""
        task_config, task_id = self.task_info(body, task, taskcluster_exchange)
        log.debug('body:\n%s', body)
        message = 'Task %s message: %s' % (task_id, task_config['message'],)
        for attempt in range(5):
            try:
                client = boto3.client(self.name,
                                      aws_access_key_id=self.access_key_id,
                                      aws_secret_access_key=self.secret_access_key)

                client.publish(TopicArn=task_config['arn'], Message=message)
                log.info('Notified with SNS for task %s' % task_id)
                return
            except Boto3Error as b3e:
                log.exception('Attempt %s: Boto3Error %s', str(attempt), b3e.message)
        else:
            log.exception('Could not notify %s via SNS for task %s', task_config['arn'], task_id)
