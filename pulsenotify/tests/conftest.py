import uvloop
import pytest

@pytest.fixture()  # TODO: write tests for notify functions
def fake_notifying_objects():
    """
        Supplies objects to be passed into
        notify(self, channel, body, envelope, properties, task, taskcluster_exchange)
    """
    from pickle import load
    notify_args = {}
    for arg in ('body', 'envelope', 'properties', 'task', 'taskcluster_exchange',):
        with open('pulsenotify/tests/mason_jar/%s.p' % arg, 'rb') as f:
            notify_args[arg] = load(f)
    return notify_args


@pytest.fixture()
def event_loop():
    """
        Since pulse-notify creates an event loop on initialization,
        try and use it for the first test after which it is closed.
        Then use a new loop every time.
    """
    from pulsenotify import event_loop as pn_loop
    return uvloop.new_event_loop() if pn_loop.is_closed() else pn_loop

@pytest.fixture()
def task_ids():
    return {
        'REAL_TASK': 'dacr5qmDQlqVl-BI_BdnBw',
        'FAKE_TASK': 'connorsheehanlolololol',
    }
