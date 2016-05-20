import smtplib
import logging
from smtplib import SMTPConnectError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


class Plugin(object):

    def __init__(self, config):
        self.email = config['email']
        self.passwd = config['passwd']
        self.host = config['host']
        self.port = config['port']

    @property
    def name(self):
        return 'smtp'

    async def notify(self, task_config):
        email_message = MIMEMultipart()
        email_message['Subject'] = task_config['subject']
        email_message['To'] = ', '.join(task_config['recipients'])
        email_message.attach(MIMEText(task_config['body']))

        try:
            s = smtplib.SMTP(self.host, self.port)
            s.ehlo()
            s.starttls()
            s.login(self.email, self.passwd)
            s.sendmail(self.email, task_config['recipients'], email_message.as_string())
            s.quit()
            print("[!] Notified on smtp!")
        except SMTPConnectError as ce:
            log.exception('[!] SMTPConnectError: %s', ce.message)
