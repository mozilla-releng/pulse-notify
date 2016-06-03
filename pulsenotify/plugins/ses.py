import boto3
from boto3.exceptions import Boto3Error
import logging
import os
import datetime

from . import AWSPlugin
from pulsenotify.util import async_time_me
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import PackageLoader, Environment

log = logging.getLogger(__name__)

env = Environment(loader=PackageLoader('pulsenotify', 'templates'))


class Plugin(AWSPlugin):

    def __init__(self):
        super().__init__()
        self.from_email = os.environ['SES_EMAIL']
        self.template = env.get_template('email_template.html') if bool(os.environ['SMTP_TEMPLATE']) == True else None

    @async_time_me
    async def notify(self, channel, body, envelope, properties, task, taskcluster_exchange):
        subject, message, task_config, task_id = self.task_info(body, task, taskcluster_exchange)

        email_message = MIMEMultipart()
        email_message['Subject'] = subject

        if self.template:
            rendered_email = self.template.render(subject=subject,
                                                  body=message,
                                                  date=datetime.datetime.now().strftime('%b %d, %Y'),
                                                  logs=self.get_logs_urls(task_id, body['status']['runs']))
            email_message.attach(MIMEText(rendered_email, 'html'))
        else:
            email_message.attach(MIMEText(message, 'text'))

        for attempt in range(5):
            try:
                ses = boto3.client(self.name,
                                    aws_access_key_id=self.access_key_id,
                                    aws_secret_access_key=self.secret_access_key,
                                    region_name='us-west-2'
                )

                raw_message = {'Data': email_message.as_string()}

                ses.send_raw_email(RawMessage=raw_message,
                                   Source=self.from_email,
                                   Destinations=task_config['recipients']
                )

                log.info('Notified with SES for task %s' % task_id)
                return
            except Boto3Error as b3e:
                log.exception('SES attempt %s: Boto3Error - %s', str(attempt), b3e)
        else:
            log.exception('Could not notify via SES for task %s', task_id)
