import boto3
from boto3.exceptions import Boto3Error
import logging
import os
import datetime

from . import AWSPlugin
from pulsenotify.util import async_time_me
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import PackageLoader, Environment, TemplateNotFound

log = logging.getLogger(__name__)

env = Environment(loader=PackageLoader('pulsenotify', 'templates'))


class Plugin(AWSPlugin):

    def __init__(self):
        super().__init__()
        self.from_email = os.environ['SES_EMAIL']
        try:
            self.template = env.get_template('email_template.html')
            log.debug('email_template.html loaded into SES')

        except TemplateNotFound:
            log.exception('Couldn\'t find email_template.html. Defaulting to text email message.')
            self.template = None

        log.info('{} plugin initialized.'.format(self.name))

    @async_time_me
    async def notify(self, task_data, status_config):
        email_message = MIMEMultipart()
        email_message['Subject'] = status_config['subject']

        if self.template:
            log_destinations = (l['destination_url'] for l in task_data.log_data())
            rendered_email = self.template.render(subject=status_config['subject'],
                                                  body=status_config['message'],
                                                  date=datetime.datetime.now().strftime('%b %d, %Y'),
                                                  logs=log_destinations,
                                                  inspector_url=task_data.inspector_url)
            email_message.attach(MIMEText(rendered_email, 'html'))
        else:
            email_message.attach(MIMEText(status_config['message'], 'text'))

        #  Set headers to create email threads
        thread_id = '<{task_group_id}@{thread_domain}>'.format(task_group_id=task_data.task_group_id,
                                                               thread_domain=os.environ.get('EMAIL_THREADING_DOMAIN',
                                                                                            'mozilla.com'))
        email_message.add_header('In-Reply-To', thread_id)
        email_message.add_header('References', thread_id)

        for attempt in range(5):
            try:
                ses = boto3.client(self.name,
                                   aws_access_key_id=self.access_key_id,
                                   aws_secret_access_key=self.secret_access_key,
                                   region_name='us-west-2')

                raw_message = {'Data': email_message.as_string()}

                ses.send_raw_email(RawMessage=raw_message,
                                   Source=self.from_email,
                                   Destinations=status_config['emails'])

                log.info('Notified with SES for %r', task_data)
                return
            except Boto3Error as b3e:
                log.exception('SES attempt %s: Boto3Error - %s', str(attempt), b3e)
        else:
            log.exception('Could not notify via SES for %s', task_data)
