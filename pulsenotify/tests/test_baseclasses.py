import pytest


class TestBasePlugin:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins import BasePlugin
        return BasePlugin()

    # def test_get_logs_urls(self, plugin, task_ids):
    #     import os
    #     urls = plugin.get_logs_urls(task_ids['REAL_TASK'], [{'runId': '0'}])
    #     correct_url = 'https://{bucket}.s3.amazonaws.com/{resource}'.format(bucket=os.environ['S3_BUCKET'],
    #                                                                         resource=plugin.S3_KEY_TEMPLATE.format(task_ids['REAL_TASK'], '0'))
    #     assert len(urls) == 1
    #     assert urls[0] == correct_url


class TestAWSPlugin:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins import AWSPlugin
        return AWSPlugin()

    def test_constructor(self, plugin):
        import os
        assert plugin.access_key_id == os.environ['AWS_ACCESS_KEY_ID']
        assert plugin.secret_access_key == os.environ['AWS_SECRET_ACCESS_KEY']
