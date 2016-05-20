import boto3


class Plugin(object):

    def __init__(self, config):
        self.access_key_id = config['aws_access_key_id']
        self.secret_access_key = config['aws_secret_access_key']

    @property
    def name(self):
        return 'sns'

    async def notify(self, task_config):
        """Perform the notification (ie email relevant addresses)"""
        client = boto3.client('sns', aws_access_key_id=self.access_key_id,
                              aws_secret_access_key=self.secret_access_key)

        client.publish(TopicArn=task_config['arn'], Message=task_config['message'])
        print('[!] Notified on sns!')
