#!/usr/bin/env python3

import logging
import sys
import logging.handlers

from src.config import Config, CONFKEY_LOG_FILE, CONFKEY_SYSTEMD, CONFKEY_LOG_PRINT, CONFKEY_LOG_LEVEL, CONFKEY_LOG_MAX_BYTES, \
    CONFKEY_LOG_MAX_COUNT
from src.runner.runner import Runner


_logger = logging.getLogger(__name__)


def init_logging(config):
    handlers = []

    format_with_ts = '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
    format_no_ts = '[%(levelname)8s] %(name)s: %(message)s'

    log_file = Config.get_str(config, CONFKEY_LOG_FILE)
    log_level = Config.get_loglevel(config, CONFKEY_LOG_LEVEL, logging.INFO)
    print_console = Config.get_bool(config, CONFKEY_LOG_PRINT, False)
    runs_as_systemd = Config.get_bool(config, CONFKEY_SYSTEMD, False)

    if log_file:
        max_bytes = Config.get_int(config, CONFKEY_LOG_MAX_BYTES, 1048576)
        max_count = Config.get_int(config, CONFKEY_LOG_MAX_COUNT, 5)
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
        config = Config.load()

        init_logging(config)

        runner = Runner()
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
