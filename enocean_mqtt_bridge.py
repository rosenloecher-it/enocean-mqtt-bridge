#!/usr/bin/env python3

import logging
import sys
import logging.handlers

from src.config import ConfMainKey, Config
from src.process import Process

_logger = logging.getLogger("main")


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
    process = None

    try:
        config = {}
        Config.load(config)

        init_logging(config)

        process = Process(config)
        process.init_devices()
        process.connect_mqtt()
        process.connect_enocean()
        process.run()

        # 1/0

        return 0

    except KeyboardInterrupt:
        # if process is not None:
        #     process.close()
        return 0

    except Exception as ex:
        _logger.exception(ex)
        # no process.close() to signal abnomal termination!
        return 1

    finally:
        if process is not None:
            process.close()


if __name__ == '__main__':
    sys.exit(main())
