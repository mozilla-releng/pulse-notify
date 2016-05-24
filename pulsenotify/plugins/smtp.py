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

        for i in range(5):
            try:
                s = smtplib.SMTP(self.host, self.port)
                s.ehlo()
                s.starttls()
                s.login(self.email, self.passwd)
                s.sendmail(self.email, task_config['recipients'], email_message.as_string())
                s.quit()
                print("[!] Notified on smtp!")
                return
            except SMTPConnectError as ce:
                log.exception('[!] Attempt %s: SMTPConnectError %s', str(i), ce.message)
        else:
            log.exception('[!] Could not connect to %s with login %s: %s', self.host, self.email)
