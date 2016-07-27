import pytest


class TestIRC:

    @pytest.fixture()
    def plugin(self, event_loop):
        from pulsenotify.plugins.irc import Plugin
        return Plugin(loop=event_loop)

    @pytest.mark.asyncio
    async def test_constructor(self, plugin):
        assert hasattr(plugin, 'notify')
