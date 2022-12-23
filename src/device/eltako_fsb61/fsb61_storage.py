import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from src.storage import Storage, StorageException


class StorageKey(Enum):
    VALUE = "VALUE"
    TIME_SINCE = "TIME_SINCE"
    TIME_UPDATE = "TIME_UPDATE"
    TIME_LAST_OBSERVATION = "TIME_LAST_OBSERVATION"


class Fsb61Storage(Storage):

    def __init__(self, device_name):
        super().__init__()

        self._name = device_name + ".storage"

        self.storage_max_age: Optional[int] = None  # age in seconds
        self.__logger: Optional[logging.Logger] = None

    @property
    def _logger(self):
        if self.__logger:
            return self.__logger

        self.__logger = logging.getLogger(self._name)
        return self.__logger

    def clear(self):
        if self._data is not None:
            self.delete(StorageKey.TIME_LAST_OBSERVATION.value)
            self.delete(StorageKey.TIME_SINCE.value)
            self.delete(StorageKey.TIME_UPDATE.value)
            self.delete(StorageKey.VALUE.value)

    def load(self):
        raise NotImplementedError("use restore instead!")

    def restore(self, time):
        """restore old STATE when in time"""
        self.clear()

        try:
            super(Fsb61Storage, self).load()
        except StorageException as ex:
            if self._logger:
                self._logger.exception(ex)

        def check_time_and_error() -> bool:
            last_observation = self.get(StorageKey.TIME_LAST_OBSERVATION.value)
            if not last_observation:
                return False
            diff_seconds = (time - last_observation).total_seconds()
            if diff_seconds > self.storage_max_age:
                return False
            return True

        def invalidate_values():
            self.delete(StorageKey.TIME_UPDATE.value)
            self.delete(StorageKey.VALUE.value)

        if not check_time_and_error():
            if self._logger:
                self._logger.info("storage: invalid/obsolete settings found. => reset, calibration needed.")
            return invalidate_values()

        value = self.get(StorageKey.VALUE.value)
        if value is not None and not isinstance(value, int):
            try:
                value = float(value)
            except ValueError:
                value = None
                if self._logger:
                    self._logger.warning(
                        "storage: cannot parse %s (%s) as float!", StorageKey.VALUE_SUCCESS.value, value)

        if value is None:
            return  # None is valid value

        if value < 0 or value > 100:
            return invalidate_values()

        # success

    @property
    def since(self) -> Optional[datetime]:
        return self.get(StorageKey.TIME_SINCE.value)

    @property
    def value(self) -> float:
        return self.get(StorageKey.VALUE.value)

    def save_value(self, value: float, time: datetime):

        last_value = self.value

        self.set(StorageKey.VALUE.value, value)
        self.set(StorageKey.TIME_UPDATE.value, time)
        self.set(StorageKey.TIME_LAST_OBSERVATION.value, time)

        if last_value != value:
            self.set(StorageKey.TIME_SINCE.value, time)

        self.save()

    def save_touched(self, time: datetime):
        self.set(StorageKey.TIME_LAST_OBSERVATION.value, time)
        self.save()

    def save(self):
        try:
            super(Fsb61Storage, self).save()
        except StorageException as ex:
            if self._logger:
                self._logger.exception(ex)
