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
        assert hasattr(plugin, 'notify')
