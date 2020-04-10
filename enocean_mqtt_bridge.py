#!/usr/bin/env python3

import sys
import logging.handlers

from src.config import ConfMainKey, Config
from src.logging_helper import LoggingHelper
from src.process.live_worker import LiveWorker
from src.process.teach_worker import TeachWorker

_logger = logging.getLogger("main")


def main():
    worker = None

    try:
        config = {}
        Config.load(config)

        LoggingHelper.init(config)

        if config.get(ConfMainKey.TEACH.value):
            worker = TeachWorker()
        else:
            worker = LiveWorker()

        worker.open(config)
        worker.run()

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
        if worker is not None:
            worker.close()


if __name__ == '__main__':
    sys.exit(main())
