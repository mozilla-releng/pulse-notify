import argparse
import json
import logging
from pulsenotify.consumer import BaseConsumer, ReleaseConsumer
from pulsenotify import event_loop
from pulsenotify.worker import worker


log = logging.getLogger(__name__)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True,
                        type=argparse.FileType("r"))
    parser.add_argument("-v", "--verbose", dest="loglevel",
                        action="store_const", const=logging.DEBUG,
                        default=logging.INFO)
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel, format="%(message)s")

    config = json.load(args.config)
    event_loop.run_until_complete(worker(config,
                                         BaseConsumer(config['notify'])
                                         )
                                  )
    event_loop.run_forever()

if __name__ == '__main__':
    cli()
