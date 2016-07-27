import smtplib
import logging
import datetime
import os

from . import BasePlugin
from smtplib import SMTPConnectError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import PackageLoader, Environment, TemplateNotFound
from pulsenotify.util import async_time_me


log = logging.getLogger(__name__)

env = Environment(loader=PackageLoader('pulsenotify', 'templates'))


class Plugin(BasePlugin):
    """
    SMTP Plugin for the Pulse Notification system.

    The following environment variables must be present for the plugin to function:
        - SMTP_EMAIL (to send notifications from)
        - SMTP_PASSWD (of email)
        - SMTP_HOST (SMTP host domain)
        - SMTP_PORT (port of host)
    """
    def __init__(self):
        self.email = os.environ['SMTP_EMAIL']
        self.passwd = os.environ['SMTP_PASSWD']
        self.host = os.environ['SMTP_HOST']
        self.port = os.environ['SMTP_PORT']
        try:
            self.template = env.get_template('email_template.html')
            log.debug('email_template.html loaded into SES')

        except TemplateNotFound:
            log.exception('Couldn\'t find email_template.html. Defaulting to text email message.')
            self.template = None
        log.info('%s plugin initialized', self.name)

    @async_time_me
    async def notify(self, task_data, exchange_config):
        email_message = MIMEMultipart()
        email_message['Subject'] = exchange_config['subject']
        email_message['To'] = ', '.join(exchange_config['emails'])

        if self.template:
            log_destinations = (l['destination_url'] for l in task_data.log_data())
            rendered_email = self.template.render(exchange_config,
                                                  date=datetime.datetime.now().strftime('%b %d, %Y'),
                                                  subject=exchange_config['subject'],
                                                  body=exchange_config['message'],
                                                  logs=log_destinations)
            email_message.attach(MIMEText(rendered_email, 'html'))
        else:
            email_message.attach(MIMEText(exchange_config['message'], 'text'))

        for attempt in range(5):
            try:
                s = smtplib.SMTP(self.host, self.port)
                s.ehlo()
                s.starttls()
                s.login(self.email, self.passwd)
                s.sendmail(self.email, exchange_config['emails'], email_message.as_string())
                s.quit()
                log.info("Notified on smtp for %r", task_data)
                return
            except SMTPConnectError as ce:
                log.exception('Attempt %s: SMTPConnectError %s', str(attempt), ce.message)
        else:
            log.exception('Could not connect to %s with login %s:%s for task %r', self.host, self.email, task_data)
