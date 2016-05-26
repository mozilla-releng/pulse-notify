import argparse
import json
import logging
import os
import sys  # TODO: remove when in prod (only use is to send log to stdout)
from blessings import Terminal
from pulsenotify.consumer import NotifyConsumer
from pulsenotify import event_loop
from pulsenotify.worker import worker


log = logging.getLogger(__name__)


class ColoredFormatter(logging.Formatter):
    """
    Credits: https://gist.github.com/exhuma/8147910
    """

    def __init__(self, terminal, *args, **kwargs):
        super(ColoredFormatter, self).__init__(*args, **kwargs)
        self._terminal = terminal

    def format(self, record):
        output = super(ColoredFormatter, self).format(record)
        if record.levelno >= logging.CRITICAL:
            line_color = self._terminal.bold_yellow_on_red
        elif record.levelno >= logging.ERROR:
            line_color = self._terminal.red
        elif record.levelno >= logging.WARNING:
            line_color = self._terminal.yellow
        elif record.levelno >= logging.INFO:
            line_color = self._terminal.green
        else:
            line_color = self._terminal.white
        return line_color(output)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", dest="loglevel",
                        action="store_const", const=logging.DEBUG,
                        default=logging.INFO)
    args = parser.parse_args()

    terminal = Terminal()
    clifmt = ColoredFormatter(
        terminal,
        '%(asctime)s [%(threadName)s] %(levelname)-10s %(message)s')
    root_logger = logging.getLogger()
    clihandler = logging.StreamHandler(sys.stdout)
    clihandler.setFormatter(clifmt)
    root_logger.setLevel(logging.NOTSET)
    root_logger.addHandler(clihandler)


    try:
        event_loop.run_until_complete(worker(NotifyConsumer(os.environ['PN_SERVICES'].split(':'))))
        event_loop.run_forever()
    except KeyboardInterrupt as ke:
        # TODO: make better shutdown
        log.exception('KeyboardInterrupt registered: exiting.')
        event_loop.stop()
        while event_loop.is_running():
            pass
        event_loop.close()
        exit()


if __name__ == '__main__':
    cli()
