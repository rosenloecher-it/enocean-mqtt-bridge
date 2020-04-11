import datetime
import json
import logging
from enum import Enum
from typing import Optional

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.conf_device_key import ConfDeviceKey
from src.device.device_exception import DeviceException
from src.enocean_connector import EnoceanMessage
from src.storage import Storage, StorageException
from src.tools import Tools


class StorageKey(Enum):
    VALUE_SUCCESS = "VALUE_SUCCESS"
    TIME_SUCCESS = "TIME_SUCCESS"
    VALUE_ERROR = "VALUE_ERROR"
    TIME_ERROR = "TIME_ERROR"
    TIME_LAST_OBSERVATION = "TIME_LAST_OBSERVATION"


class HandleValue(Enum):
    CLOSED = "CLOSED"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"
    OPEN = "OPEN"
    TILTED = "TILTED"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)

    @classmethod
    def is_success(cls, state):
        return state in [cls.CLOSED, cls.OPEN, cls.TILTED]

    @classmethod
    def parse(cls, text: str):
        for e in cls:
            if text == e.value:
                return e

        return None


class HandlePosAttr(Enum):
    RSSI = "RSSI"
    SINCE = "SINCE"
    TIMESTAMP = "TIMESTAMP"
    STATE = "STATE"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


class FFG7BDevice(BaseDevice):
    """Specialized class to forward notfications of Eltako FFG7B-rw (Eltako TF-FGB)
    windows/door handles. Output is a json dict with values of `HandleValues`.
    Additionally there is a `SINCE` field (JSON) which indicates the last change time.

    No information is sent to the device!
    """

    def __init__(self, name):
        super().__init__(name)

        # default config values
        self._enocean_rorg = 0xf6
        self._enocean_func = 0x10
        self._enocean_type = 0x00

        self._write_since_no_error = True
        self._write_since = False

        self._storage = Storage()

    def set_config(self, config):
        super().set_config(config)

        self._write_since = Config.post_process_bool(self._config, ConfDeviceKey.WRITE_SINCE, False)
        self._write_since_no_error = Config.post_process_bool(self._config,
                                                              ConfDeviceKey.WRITE_SINCE_SEPARATE_ERROR, True)
        self._restore_last_max_diff = Config.post_process_int(self._config,
                                                              ConfDeviceKey.RESTORE_LAST_MAX_DIFF, 15)

        storage_file = Config.post_process_str(self._config, ConfDeviceKey.STORAGE_FILE, None)
        self._storage.set_file(storage_file)

        try:
            self._storage.load()
        except StorageException as ex:
            self._logger.exception(ex)

    def _determine_and_store_since(self, value_enum: HandleValue):
        success_value = HandleValue.is_success(value_enum)
        if not self._write_since_no_error or success_value:
            key_state = StorageKey.VALUE_SUCCESS.value
            key_time = StorageKey.TIME_SUCCESS.value
        else:
            key_state = StorageKey.VALUE_ERROR.value
            key_time = StorageKey.TIME_ERROR.value

        if success_value:
            self._storage.delete(StorageKey.VALUE_ERROR.value)
            self._storage.delete(StorageKey.TIME_ERROR.value)

        value_since = self._storage.get(key_state)
        time_since = self._storage.get(key_time)
        if value_since != value_enum.value:
            value_since = value_enum.value
            time_since = None

        if time_since is None:
            time_since = self._now()
            self._storage.set(key_state, value_since)
            self._storage.set(key_time, time_since)

            try:
                self._storage.save()
            except StorageException as ex:
                self._logger.exception(ex)

        return time_since

    def _create_message(self, value: HandleValue, since: Optional[datetime.datetime],
                        rssi: Optional[int] = None, timestamp: Optional[datetime.datetime] = None):

        if not timestamp:
            timestamp = self._now()

        data = {
            HandlePosAttr.TIMESTAMP.value: timestamp.isoformat(),
            HandlePosAttr.STATE.value: value.value
        }
        if rssi is not None:
            data[HandlePosAttr.RSSI.value] = rssi
        if since is not None:
            data[HandlePosAttr.SINCE.value] = since.isoformat()

        json_text = json.dumps(data)
        return json_text

    @classmethod
    def extract_handle_state(self, value):
        if value == 3:
            return HandleValue.CLOSED
        elif value == 2:
            return HandleValue.OPEN
        elif value == 1:
            return HandleValue.TILTED
        else:
            return HandleValue.ERROR

    def process_enocean_message(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            return

        self._update_enocean_activity()

        data = self._extract_message(packet)
        self._logger.debug("proceed_enocean - got: %s", data)

        rssi = packet.dBm  # if hasattr(packet, "dBm") else None

        try:
            value = self.extract_handle_state(data.get("WIN"))
        except DeviceException as ex:
            self._logger.exception(ex)
            value = HandleValue.ERROR

        if value == HandleValue.ERROR and self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("proceed_enocean - pickled error packet:\n%s", Tools.pickle_packet(packet))

        if self._write_since:
            since = self._determine_and_store_since(value)
        else:
            since = None

        message = self._create_message(value, since, rssi=rssi)
        self._publish_mqtt(message)

    def _restore_last_state(self):
        """restore old STATE when in time"""
        last_observation = self._storage.get(StorageKey.TIME_LAST_OBSERVATION.value)
        if not last_observation:
            return
        diff_seconds = (self._now() - last_observation).total_seconds()
        if diff_seconds > self._restore_last_max_diff:
            return
        if self._storage.get(StorageKey.TIME_ERROR.value) is not None:
            return

        last_value = self._storage.get(StorageKey.VALUE_SUCCESS.value)
        last_since = self._storage.get(StorageKey.TIME_SUCCESS.value)
        if not last_value or not last_since:
            return

        last_handle_value = HandleValue.parse(last_value)
        if not HandleValue.is_success(last_handle_value):
            return

        self._logger.info("old state '%s' (%s) restored.", last_handle_value, last_observation)
        message = self._create_message(last_handle_value, last_since, timestamp=last_observation)
        self._publish_mqtt(message)

    def open_mqtt(self):
        super().open_mqtt()

        self._restore_last_state()

    def close_mqtt(self):
        super().close_mqtt()

        self._storage.set(StorageKey.TIME_LAST_OBSERVATION.value, self._now())
        try:
            self._storage.save()
        except StorageException as ex:
            self._logger.exception(ex)
