import pytest


class TestBasePlugin:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins import BasePlugin
        return BasePlugin()


class TestAWSPlugin:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins import AWSPlugin
        return AWSPlugin()

    def test_constructor(self, plugin):
        import os
        assert plugin.access_key_id == os.environ['AWS_ACCESS_KEY_ID']
        assert plugin.secret_access_key == os.environ['AWS_SECRET_ACCESS_KEY']
        assert hasattr(plugin, 'notify')
