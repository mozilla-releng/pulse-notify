from pulsenotify.plugins.base_plugin import BasePlugin
import boto3
from boto3.exceptions import Boto3Error
import logging

log = logging.getLogger(__name__)


class Plugin(BasePlugin):
    """
    Amazon SNS Plugin for the Pulse Notification system

    On startup, the config file must include an object with the following elements in the schema:
        - aws_access_key_id
        - aws_secret_access_key

    In each task, under extra/<desired exchange>, there must be an object with the following schema:
        - arn (Amazon resource number of SNS topic to deliver notification to)
        - message (body of the notification message)
    """
    def __init__(self, config):
        self.access_key_id = config['aws_access_key_id']
        self.secret_access_key = config['aws_secret_access_key']
        log.info('%s plugin initialized', self.name)

    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        """Perform the notification (ie email relevant addresses)"""
        task_config = self.get_notify_section(task, taskcluster_exchange)
        task_id = body["status"]["taskId"]
        message = 'Task %s message: %s'.format(task_id, task_config['message'])
        for attempt in range(5):
            try:
                client = boto3.client(self.name,
                                      aws_access_key_id=self.access_key_id,
                                      aws_secret_access_key=self.secret_access_key)

                client.publish(TopicArn=task_config['arn'], Message=message)
                log.info('Notified with SNS!')
                return
            except Boto3Error as b3e:
                log.exception('Attempt %s: Boto3Error %s', str(attempt), b3e.message)
        else:
            log.exception('Could not notify %s via SNS for task %s', task_config['arn'], task_id)