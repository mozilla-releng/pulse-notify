import pytest
from unittest.mock import MagicMock


@pytest.fixture()
def task_data(task_ids):
    from pulsenotify.consumer import TaskData
    from json import dumps
    body = dumps({
        'status': {
            'taskId': task_ids['REAL_TASK']
        }
    })
    envelope = MagicMock()
    envelope.exchange_name = '/task-completed'
    properties = object()

    return TaskData(body, envelope, properties)


class TestConsumer:

    @pytest.fixture(scope='class')
    def consumer(self):
        from pulsenotify.consumer import NotifyConsumer
        return NotifyConsumer()

    @pytest.fixture(scope='class')
    def notify_config(self, consumer, task_data):
        return consumer.generate_notification_configuration(task_data)

    def test_constructor(self, consumer):
        import os

        assert hasattr(consumer, 'identities')
        assert hasattr(consumer, 'notifiers')
        for service in os.environ['PN_SERVICES'].split(':'):
            assert service in consumer.notifiers
        assert hasattr(consumer, 'routing_keys')
        assert hasattr(consumer, 'exchanges')


@pytest.mark.asyncio
async def test_get_log():
    from pulsenotify.consumer import get_log
    bbb_log_url = 'https://queue.taskcluster.net/v1/task/33L76kSaRryFXFsiwzYo2w/runs/0/artifacts/public/properties.json'
    aws_log_url = 'https://queue.taskcluster.net/v1/task/QWfpy1x1RXWr2aEiFiHkww/runs/0/artifacts/public/logs/live.log'

    artifact_bbb = await get_log(bbb_log_url, 'buildbot-bridge')
    artifact_aws = await get_log(aws_log_url, 'aws-provisioner-v1')

    assert type(artifact_bbb) is str
    assert '33L76kSaRryFXFsiwzYo2w' in str(artifact_bbb)

    assert type(artifact_aws) is str
    assert 'QWfpy1x1RXWr2aEiFiHkww' in str(artifact_aws)
