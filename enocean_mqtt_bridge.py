#!/usr/bin/env python3

import logging
import sys
import logging.handlers

from src.config import ConfMainKey, Config
from src.runner.service_runner import ServiceRunner
from src.runner.teach_runner import TeachRunner

_logger = logging.getLogger(__name__)


def init_logging(config):
    handlers = []

    format_with_ts = '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
    format_no_ts = '[%(levelname)8s] %(name)s: %(message)s'

    log_file = config[ConfMainKey.LOG_FILE.value]
    log_level = config[ConfMainKey.LOG_LEVEL.value]
    print_console = config[ConfMainKey.LOG_PRINT.value]
    runs_as_systemd = config[ConfMainKey.SYSTEMD.value]

    if log_file:
        max_bytes = config[ConfMainKey.LOG_MAX_BYTES.value]
        max_count = config[ConfMainKey.LOG_MAX_COUNT.value]
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=int(max_bytes),
            backupCount=int(max_count)
        )
        formatter = logging.Formatter(format_with_ts)
        handler.setFormatter(formatter)
        handlers.append(handler)

    if runs_as_systemd:
        log_format = format_no_ts
    else:
        log_format = format_with_ts

    if print_console or runs_as_systemd:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        format=log_format,
        level=log_level,
        handlers=handlers
    )


def main():
    runner = None

    try:
        config = {}
        Config.load(config)

        init_logging(config)

        if config.get(ConfMainKey.TEACH.value):
            runner = TeachRunner()
        else:
            runner = ServiceRunner()

        runner.open(config)
        runner.run()

        return 0

    except KeyboardInterrupt:
        # if runner is not None:
        #     runner.close()
        return 0

    except Exception as ex:
        _logger.exception(ex)
        # no runner.close() to signal abnomal termination!
        return 1

    finally:
        if runner is not None:
            runner.close()


if __name__ == '__main__':
    sys.exit(main())
