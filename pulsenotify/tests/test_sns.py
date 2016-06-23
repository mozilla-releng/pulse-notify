import pytest


class TestSNS:

    @pytest.fixture(scope='module')
    def plugin(self):
        from pulsenotify.plugins.sns import Plugin
        return Plugin()

    def test_constructor(self, plugin):
        import os
        assert plugin.arn == os.environ['SNS_ARN']
