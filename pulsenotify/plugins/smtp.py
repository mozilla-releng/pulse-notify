import smtplib
import logging
import datetime
import os

from . import BasePlugin
from smtplib import SMTPConnectError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import PackageLoader, Environment
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
        - SMTP_TEMPLATE (True/False indicator to use template)

    In each task, under extra/notification/<desired exchange>, there must be an object with the following schema:
        - subject (of email)
        - recipients (who to notify)
        - body (of email in text format)
    """
    def __init__(self):
        self.email = os.environ['SMTP_EMAIL']
        self.passwd = os.environ['SMTP_PASSWD']
        self.host = os.environ['SMTP_HOST']
        self.port = os.environ['SMTP_PORT']
        self.template = env.get_template('email_template.html') if bool(os.environ['SMTP_TEMPLATE']) == True else None
        log.info('%s plugin initialized', self.name)

    @async_time_me
    async def notify(self, body, envelope, properties, task, task_id, taskcluster_exchange, exchange_config):
        subject, message = self.task_info(exchange_config)

        email_message = MIMEMultipart()
        email_message['Subject'] = subject
        email_message['To'] = ', '.join(exchange_config['emails'])

        if self.template:
            rendered_email = self.template.render(exchange_config,
                                                  date=datetime.datetime.now().strftime('%b %d, %Y'),
                                                  subject=subject,
                                                  body=message,
                                                  logs=self.get_logs_urls(task_id, body['status']['runs']))
            email_message.attach(MIMEText(rendered_email, 'html'))
        else:
            email_message.attach(MIMEText(message, 'text'))

        for attempt in range(5):
            try:
                s = smtplib.SMTP(self.host, self.port)
                s.ehlo()
                s.starttls()
                s.login(self.email, self.passwd)
                s.sendmail(self.email, exchange_config['emails'], email_message.as_string())
                s.quit()
                log.info("Notified on smtp for task %s" % task_id)
                return
            except SMTPConnectError as ce:
                log.exception('Attempt %s: SMTPConnectError %s', str(attempt), ce.message)
        else:
            log.exception('Could not connect to %s with login %s:%s for task %s', self.host, self.email, task_id)
