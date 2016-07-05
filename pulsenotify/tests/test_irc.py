import pytest


class TestIRC:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins.irc import Plugin
        return Plugin()

    @pytest.mark.asyncio
    async def test_notify(self, plugin, fake_notifying_objects):
        assert type(fake_notifying_objects['task']) is dict
