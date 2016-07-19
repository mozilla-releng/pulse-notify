import pytest


class TestConsumer:

    @pytest.fixture(scope='class')
    def consumer(self):
        from pulsenotify.consumer import NotifyConsumer
        return NotifyConsumer()

    def test_constructor(self, consumer):
        import os

        assert hasattr(consumer, 'identities')

        assert hasattr(consumer, 'notifiers')
        for service in os.environ['PN_SERVICES'].split(':'):
            assert service in consumer.notifiers
        assert hasattr(consumer, 'routing_keys')
        assert hasattr(consumer, 'exchanges')

    def test_generate_notification_configuration(self):
        pass
