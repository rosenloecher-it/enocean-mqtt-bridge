import logging
import sys

from src.config import ConfMainKey
from src.constant import Constant


class LoggingHelper:

    log_level = Constant.DEFAULT_LOGLEVEL

    @classmethod
    def init(cls, config):
        handlers = []

        format_with_ts = '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
        format_no_ts = '[%(levelname)8s] %(name)s: %(message)s'

        cls.log_level = config[ConfMainKey.LOG_LEVEL.value]

        log_file = config[ConfMainKey.LOG_FILE.value]
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
            level=logging.WARNING,  # disable lib loggers!
            handlers=handlers
        )

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Purpose: The Enocean lib is quite verbose in dEBUG mode, so explicit config loglevel for own loggers
        withozu using the global loglevel,

        :param name: Logger name
        """
        logger = logging.getLogger(name)
        logger.setLevel(cls.log_level)
        return logger
