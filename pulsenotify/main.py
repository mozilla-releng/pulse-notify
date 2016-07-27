import logging
import sys
from pulsenotify.consumer import NotifyConsumer
from pulsenotify import event_loop
from pulsenotify.worker import worker


log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, format='%(asctime)s [%(levelname)s] %(message)s', level=logging.NOTSET)


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
    cli()
