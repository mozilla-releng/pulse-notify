import pytest


class TestSES:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins.ses import Plugin
        return Plugin()

    def test_constructor(self, plugin):
        import os
        assert plugin.secret_access_key == os.environ['AWS_SECRET_ACCESS_KEY']
        assert plugin.access_key_id == os.environ['AWS_ACCESS_KEY_ID']
        assert plugin.from_email == os.environ['SES_EMAIL']
