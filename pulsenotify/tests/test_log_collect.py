import pytest


class TestLogCollect:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins.log_collect import Plugin
        return Plugin()

    def test_constructor(self, plugin):
        import os

        assert plugin.name == 'log_collect'
        assert plugin.s3_bucket == os.environ['S3_BUCKET']

    @pytest.mark.asyncio
    async def test_get_artifact(self):
        from pulsenotify.plugins.log_collect import get_log
        bbb_log_url = 'https://queue.taskcluster.net/v1/task/33L76kSaRryFXFsiwzYo2w/runs/0/artifacts/public/properties.json'
        aws_log_url = 'https://queue.taskcluster.net/v1/task/QWfpy1x1RXWr2aEiFiHkww/runs/0/artifacts/public/logs/live.log'

        artifact_bbb = await get_log(bbb_log_url, 'buildbot-bridge')
        artifact_aws = await get_log(aws_log_url, 'aws-provisioner-v1')

        assert type(artifact_bbb) is str
        assert '33L76kSaRryFXFsiwzYo2w' in str(artifact_bbb)

        assert type(artifact_aws) is str
        assert 'QWfpy1x1RXWr2aEiFiHkww' in str(artifact_aws)
