import pytest

from pulsenotify.util import retry_connection, RetriesExceededError


def _extract_chained_exception_message(pytest_exec_info):
    return pytest_exec_info.getrepr().chain[0][1].message


class _CustomException(Exception):
    pass


@pytest.mark.asyncio
async def test_retry_connection_returns_fetched_value():
    async def passing_function():
        return "I'm passing"

    assert await retry_connection(passing_function) == "I'm passing"


@pytest.mark.asyncio
async def test_retry_connection_passes_function_arguments():
    async def function_with_args(one_arg, two_args):
        return one_arg, two_args

    value = await retry_connection(function_with_args, 'this one arg', 'this other arg')

    assert value == ('this one arg', 'this other arg')


@pytest.mark.asyncio
async def test_retry_connection_chains_value_error_when_fetched_value_is_falsey():
    async def always_empty_function():
        return None

    with pytest.raises(RetriesExceededError) as e:
        await retry_connection(always_empty_function, sleep_interval_in_s=0.1)

    assert _extract_chained_exception_message(e) == \
        'ValueError: "always_empty_function" returned a falsey value: None'


@pytest.mark.asyncio
async def test_retry_connection_chains_latest_failure():
    async def error_function():
        raise _CustomException("I won't pass")

    with pytest.raises(RetriesExceededError) as e:
        await retry_connection(error_function, sleep_interval_in_s=0.1)

    assert _extract_chained_exception_message(e) == \
        "test_utils._CustomException: I won't pass"


@pytest.mark.asyncio
async def test_retry_connection_allows_retries_to_be_by_passed():
    async def error_function():
        raise _CustomException("I won't pass")

    with pytest.raises(_CustomException):
        await retry_connection(error_function, sleep_interval_in_s=0.1, by_pass_exceptions=(_CustomException,))


class TestFetchTask:

    @pytest.mark.asyncio
    async def test_real_task(self, task_ids):
        from pulsenotify.util import fetch_task

        resp = await fetch_task(task_ids['REAL_TASK'])

        assert type(resp) is dict
        assert resp['taskGroupId'] == "3NLV9LrRSiyaS-zop5EdAw"

    @pytest.mark.asyncio
    async def test_fake_task(self, task_ids):
        from pulsenotify.util import fetch_task

        resp = await fetch_task(task_ids['FAKE_TASK'])

        assert resp['code'] == 'InvalidRequestArguments'
