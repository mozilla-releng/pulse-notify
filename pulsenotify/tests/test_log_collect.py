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
    async def test_get_artifact(self, plugin, task_ids):
        artifact = await plugin.get_artifact(task_ids['REAL_TASK'], '0')
        assert type(artifact) is str
        assert task_ids['REAL_TASK'] in artifact

    @pytest.mark.asyncio
    async def test_notify(self, plugin):
        plugin.notify()
        assert plugin.name == 'log_collect'
