import logging
import sys
import os
from pulsenotify.consumer import NotifyConsumer
from pulsenotify import event_loop
from pulsenotify.worker import worker


log = logging.getLogger(__name__)



def cli():
    try:
        event_loop.run_until_complete(worker(NotifyConsumer()))
        event_loop.run_forever()
    except KeyboardInterrupt:
        # TODO: make better shutdown
        log.exception('KeyboardInterrupt registered, exiting.')
        event_loop.stop()
        while event_loop.is_running():
            pass
        event_loop.close()
        exit()


if __name__ == '__main__':
    # Get desired log level from environment, fallback to "INFO"
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    # convert the string representation of level into internal int
    log_level = logging._nameToLevel.get(log_level, logging.INFO)
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=log_level)
    cli()
