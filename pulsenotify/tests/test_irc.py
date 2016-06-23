import pytest


class TestIRC:

    @pytest.fixture(scope='module')
    def plugin(self):
        from pulsenotify.plugins.irc import Plugin
        return Plugin()
