import pytest
#from hypothesis import

class TestFetchTask:

    @pytest.mark.asyncio
    async def test_real_task(self, task_ids):
        from pulsenotify.util import fetch_task

        resp = await fetch_task(task_ids['REAL_TASK'])

        assert type(resp) is dict
        assert resp['taskGroupId'] == "BZLGDtMDRjK4YigfYqTR7Q"

    @pytest.mark.asyncio
    async def test_fake_task(self, task_ids):
        from pulsenotify.util import fetch_task

        resp = await fetch_task(task_ids['FAKE_TASK'])

        assert resp['code'] == 'InvalidRequestArguments'
