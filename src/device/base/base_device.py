import abc
import datetime
import logging
from typing import Optional

from tzlocal import get_localzone

_class_logger = logging.getLogger(__name__)


class BaseDevice(abc.ABC):
    """Encapsulates some basics."""

    def __init__(self):
        self.__name = None  # type: Optional[str]
        self.__logger_by_name = None  # type: Optional[logging.Logger]

    @property
    def _logger(self):
        if self.__logger_by_name:
            return self.__logger_by_name

        if self.__name:
            self.__logger_by_name = logging.getLogger(self.__name)
            return self.__logger_by_name

        return _class_logger

    def _set_name(self, name):
        if self.__name:
            raise RuntimeError("Initialize only once!")

        self.__name = name

    @property
    def name(self):
        return self.__name or self.__class__.__name__ + "???"

    def _now(self):
        """overwrite in test to simulate different times"""
        return datetime.datetime.now(tz=get_localzone())
