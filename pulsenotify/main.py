import argparse
import logging
import sys
from blessings import Terminal
from pulsenotify.consumer import NotifyConsumer
from pulsenotify import event_loop
from pulsenotify.worker import worker


log = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, format='%(asctime)s;\t%(levelname)s;\t%(message)s')


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('-env', '--environment', default='dev', nargs='?',
                        help='Specifies development or production environment',
                        dest='env', type=str)

    args = parser.parse_args()

    root_logger = logging.getLogger()
    clihandler = logging.StreamHandler(sys.stdout)
    root_logger.setLevel(logging.NOTSET)
    root_logger.addHandler(clihandler)

    try:
        event_loop.run_until_complete(worker(NotifyConsumer(args.env)))
        event_loop.run_forever()
    except KeyboardInterrupt as ke:
        # TODO: make better shutdown
        log.exception('KeyboardInterrupt registered, exiting.')
        event_loop.stop()
        while event_loop.is_running():
            pass
        event_loop.close()
        exit()


if __name__ == '__main__':
    cli()
