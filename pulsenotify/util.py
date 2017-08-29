import aiohttp
import asyncio
import logging
import influxdb
import os
from functools import wraps
from time import time

log = logging.getLogger(__name__)

db_cnxn = influxdb.InfluxDBClient(database=os.environ.get('INFLUXDB_NAME', 'time_notifications'))


class RetriesExceededError(Exception):
    """ Exception raised when too many retries occured """
    pass


async def retry_connection(async_func, *func_params, sleep_interval_in_s=10, by_pass_exceptions=()):
    max_attempt = 5
    current_attempt = 0

    while current_attempt < max_attempt:
        current_attempt += 1
        try:
            result = await async_func(*func_params)
            if result:
                return result
            else:
                raise ValueError('"{}" returned a falsey value: {}'.format(async_func.__name__, result))
        except by_pass_exceptions as e:
            log.debug('By pass exception "%s" met. Stopping retry mechanism.')
            raise e
        except Exception as e:
            if current_attempt < max_attempt:
                log.warn('Cannot access network. Retrying. Reason: %s', e)
            else:
                log.warn('Too many retries. Chaining latest issue...')
                raise RetriesExceededError from e

        log.warn('Fetch attempt %s failed, retrying in 10s...', current_attempt)
        await asyncio.sleep(sleep_interval_in_s)


async def fetch_task(task_id):
    log.info('Fetching task %s from Taskcluster', task_id)
    url = "https://queue.taskcluster.net/v1/task/{}".format(task_id)
    with aiohttp.Timeout(10), aiohttp.ClientSession() as session:
        response = await session.get(url)
        return await response.json()


def async_time_me(f):
    @wraps(f)
    async def timed(*args, **kw):
        t_i = time()
        result = await f(*args, **kw)
        t_f = time()

        log.debug('notify coroutine for %r took %2.4f sec', f.__module__.split('.')[-1], t_f - t_i)

        if bool(int(os.environ['INFLUXDB_RECORD'])):
            db_cnxn.write_points([{
                "measurement": "notify_timing",
                "tags": {
                    "host": os.environ.get('INFLUXDB_HOST', 'local'),
                    "service": f.__module__.split('.')[-1]
                },
                "fields": {
                    "elapsed_time": str(t_f - t_i)
                }
            }])
        return result
    return timed
