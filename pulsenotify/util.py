import aiohttp
import logging
from blessings import Terminal

log = logging.getLogger(__name__)


async def fetch_task(task_id):
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
