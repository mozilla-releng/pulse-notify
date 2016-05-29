import boto3
from boto3.exceptions import Boto3Error
import logging
import os
from . import AWSPlugin

log = logging.getLogger(__name__)


class Plugin(AWSPlugin):

    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        task_config, task_id = self.task_info(body, task, taskcluster_exchange)

        for attempt in range(5):
            try:
                client = boto3.client(self.name, aws_access_key_id=self.access_key_id,
                                      aws_secret_access_key=self.secret_access_key)

                client.send_email()  # TODO: setup AWS permissions to test
            except Boto3Error as b3e:
                log.exception('SES attempt %s: Boto3Error - %s', str(attempt), b3e)
        else:
            log.exception('Could not notify %s via SES for task %s', task_config['arn'], task_id)
