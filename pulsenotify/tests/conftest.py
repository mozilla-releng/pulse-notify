import uvloop
import pytest


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
        'REAL_TASK': '0OnFim7VQ3K4lCl0scQxuw',
        'FAKE_TASK': 'connorsheehanlolololol',
    }
