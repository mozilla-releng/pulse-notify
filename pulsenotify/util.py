import aiohttp
import logging
import influxdb
import os
from time import time
from functools import wraps
from blessings import Terminal

log = logging.getLogger(__name__)

db_cnxn = influxdb.InfluxDBClient(database='time_notifications')



async def fetch_task(task_id):
    log.info('Fetching task %s from Taskcluster', task_id)
    url = "https://queue.taskcluster.net/v1/task/{}".format(task_id)
    with aiohttp.Timeout(10), aiohttp.ClientSession() as session:
        response = await session.get(url)
        return await response.json()


async def task_term_info(body):
    task = await fetch_task(body["status"]["taskId"])
    name = task["metadata"]["name"]
    description = task["metadata"]["description"]
    task_id = body["status"]["taskId"]
    t = Terminal()
    return "{} {} {}".format(t.bold(task_id), name, t.dim(description))


def async_time_me(f):
    @wraps(f)
    async def timed(*args, **kw):
        t_i = time()
        result = await f(*args, **kw)
        t_f = time()
        log.debug('notify coroutine for %r took %2.4f sec', f.__module__.split('.')[-1], t_f - t_i)
        if bool(int(os.environ['FLUX_RECORD'])):
            db_cnxn.write_points([{
                "measurement": "notify_timing",
                "tags": {
                    "host": "local",
                    "service": "dispatch/none"
                },
                "fields": {
                    "elapsed_time": str(t_f - t_i)
                }
            }])
        return result
    return timed
