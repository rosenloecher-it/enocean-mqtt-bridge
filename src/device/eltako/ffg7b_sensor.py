import datetime
import json
import logging
from enum import Enum
from typing import Optional

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.common.eep import Eep
from src.common.json_attributes import JsonAttributes
from src.device.base.cyclic_device import CheckCyclicTask
from src.device.base.device import Device, CONFKEY_ENOCEAN_SENDER, CONFKEY_MQTT_CHANNEL_CMD
from src.device.device_exception import DeviceException
from src.enocean_connector import EnoceanMessage
from src.storage import Storage, StorageException, CONFKEY_STORAGE_MAX_AGE_SECS, CONFKEY_STORAGE_FILE
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


FFG7B_SENSOR_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_STORAGE_FILE: {"type": "string", "minLength": 1},
        CONFKEY_STORAGE_MAX_AGE_SECS: {"type": "number", "minimum": 1},
    },
    "required": [
    ],
}


class StorageKey(Enum):
    VALUE_SUCCESS = "VALUE_SUCCESS"
    TIME_SUCCESS = "TIME_SUCCESS"
    VALUE_ERROR = "VALUE_ERROR"
    TIME_ERROR = "TIME_ERROR"
    TIME_LAST_OBSERVATION = "TIME_LAST_OBSERVATION"


class HandleValue(Enum):
    CLOSED = "closed"
    ERROR = "error"
    OFFLINE = "offline"
    OPEN = "open"
    TILTED = "tilted"

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


class FFG7BSensor(Device, CheckCyclicTask):
    """Specialized class to forward notfications of Eltako FFG7B-rw (similar to Eltako TF-FGB) windows/door handles.
    Output is a json dict with values of `HandleValues`. Additionally there is a `SINCE` field (JSON) which indicates
    the last change time.

    No information is sent back to the device! Not supported by device.
    """

    DEFAULT_EEP = Eep(
        rorg=0xf6,
        func=0x10,
        type=0x00,
        direction=None,
        command=None
    )

    def __init__(self, name):
        Device.__init__(self, name)
        CheckCyclicTask.__init__(self)

        # default config values
        self._eep = self.DEFAULT_EEP.clone()

        self._storage_max_age = None  # type: Optional[int]  # age in seconds

        self._storage = Storage()

    def _set_config(self, config, skip_require_fields: [str]):
        skip_require_fields = [*skip_require_fields, CONFKEY_ENOCEAN_SENDER, CONFKEY_MQTT_CHANNEL_CMD]

        super()._set_config(config, skip_require_fields)

        schema = self.filter_required_fields(FFG7B_SENSOR_JSONSCHEMA, skip_require_fields)
        self.validate_config(config, schema)

        self._storage_max_age = config.get(CONFKEY_STORAGE_MAX_AGE_SECS, 60)

        storage_file = config.get(CONFKEY_STORAGE_FILE)
        self._storage.set_file(storage_file)

        try:
            self._storage.load()
        except StorageException as ex:
            self._logger.exception(ex)

    def _determine_and_store_since(self, value_enum: HandleValue):
        success_value = HandleValue.is_success(value_enum)
        if success_value:
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

    def _create_message(self, value: HandleValue, since: Optional[datetime.datetime], timestamp: Optional[datetime.datetime] = None):

        if not timestamp:
            timestamp = self._now()

        data = {
            JsonAttributes.DEVICE: self.name,
            JsonAttributes.STATE: value.value,
            JsonAttributes.TIMESTAMP: timestamp.isoformat(),
        }
        if since is not None:
            data[JsonAttributes.SINCE] = since.isoformat()

        json_text = json.dumps(data)
        return json_text

    def check_cyclic_tasks(self):
        self._check_and_send_offline()

    @classmethod
    def extract_handle_state(cls, value):
        if value == 3:
            return HandleValue.CLOSED
        elif value == 2:
            return HandleValue.OPEN
        elif value == 1:
            return HandleValue.TILTED
        else:
            return HandleValue.ERROR

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload  # type: RadioPacket
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return
        if packet.rorg != self._eep.rorg:
            self._logger.debug("skipped packet with rorg=%s", hex(packet.rorg))
            return

        self._reset_offline_refresh_timer()

        data = EnoceanTools.extract_packet_props(packet, self._eep)
        self._logger.debug("proceed_enocean - got: %s", data)

        try:
            value = self.extract_handle_state(data.get("WIN"))
        except DeviceException as ex:
            self._logger.exception(ex)
            value = HandleValue.ERROR

        if value == HandleValue.ERROR and self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("proceed_enocean - pickled error packet:\n%s", PickleTools.pickle_packet(packet))

        since = self._determine_and_store_since(value)

        message = self._create_message(value, since)
        self._publish_mqtt(message)

    def _restore_last_state(self):
        """restore old STATE when in time"""
        if not self._storage.initilized:
            return  # TODO race condition: MQTT conection or loaded configuration

        last_observation = self._storage.get(StorageKey.TIME_LAST_OBSERVATION.value)
        if not last_observation:
            return
        diff_seconds = (self._now() - last_observation).total_seconds()
        if diff_seconds > self._storage_max_age:
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

    def process_mqtt_message(self, message):
        pass  # do nothing

    def close_mqtt(self):
        super().close_mqtt()

        self._storage.set(StorageKey.TIME_LAST_OBSERVATION.value, self._now())
        try:
            self._storage.save()
        except StorageException as ex:
            self._logger.exception(ex)
