import pytest


class TestConsumer:

    @pytest.fixture(scope='class')
    def consumer(self):
        import os
        from pulsenotify.consumer import NotifyConsumer
        return NotifyConsumer()

    def test_constructor(self, consumer):
        import os
        for service in os.environ['PN_SERVICES'].split(':'):
            assert service in consumer.notifiers
