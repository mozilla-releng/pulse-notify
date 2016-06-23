import pytest


class TestSES:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins.ses import Plugin
        return Plugin()

    def test_constructor(self, plugin):
        import os
        assert plugin.from_email == os.environ['SES_EMAIL']
