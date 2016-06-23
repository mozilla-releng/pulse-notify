import pytest


class TestBaseClasses:

    @pytest.fixture(scope='class')
    def plugin(self):
        from pulsenotify.plugins import BasePlugin
        return BasePlugin()

    def test_get_logs_urls(self, plugin, task_ids):
        import os
        urls = plugin.get_logs_urls(task_ids['REAL_TASK'], [{'runId': '0'}])
