import datetime
import logging
from collections import namedtuple
from enum import Enum
from typing import Optional, Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.common.eep import Eep
from src.common.json_attributes import JsonAttributes
from src.device.base.cyclic_device import CheckCyclicTask
from src.device.base.device import Device, CONFKEY_ENOCEAN_SENDER, CONFKEY_MQTT_CHANNEL_CMD
from src.common.device_exception import DeviceException
from src.enocean_connector import EnoceanMessage
from src.storage import Storage, StorageException, CONFKEY_STORAGE_MAX_AGE_SECS, CONFKEY_STORAGE_FILE
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


OPENING_SENSOR_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_STORAGE_FILE: {"type": "string", "minLength": 1},
        CONFKEY_STORAGE_MAX_AGE_SECS: {
            "type": "number",
            "minimum": 1,
            "description": "After a restart the device state may be restored from file within that period of time (in seconds) "
                           "and announe that former state and overwrite a former last will message."
        },
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


class StateValue(Enum):
    CLOSED = "closed"
    OPEN = "open"
    TILTED = "tilted"

    ERROR = "error"
    OFFLINE = "offline"  # only internally used in storage

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


EepHandler = namedtuple("EepHandler", ["eep", "extract_state"])


class OpeningSensor(Device, CheckCyclicTask):
    """Multi-use window-door-sensor with heartbeat check."""

    ELTAKO_FTKB_DOUBLED_TIME = 5.0  # in seconds. telegrams are sent twice and filtered out by time

    def __init__(self, name):
        Device.__init__(self, name)
        CheckCyclicTask.__init__(self)

        self._last_packet_data: Optional[Dict[str, any]] = None
        self._last_packet_time: Optional[datetime.datetime] = None

        self._eep_handlers = [
            EepHandler(
                Eep(rorg=0xf6, func=0x10, type=0x00, direction=None, command=None),
                self.extract_state_value_from_f6_10_00
            ),
            EepHandler(
                Eep(rorg=0xd5, func=0x00, type=0x01, direction=None, command=None),
                self.extract_state_value_from_d5_00_01
            ),
        ]

        self._storage_max_age: Optional[int] = None  # age in seconds

        self._storage = Storage()

    def _set_config(self, config, skip_require_fields: [str]):
        skip_require_fields = [*skip_require_fields, CONFKEY_ENOCEAN_SENDER, CONFKEY_MQTT_CHANNEL_CMD]

        super()._set_config(config, skip_require_fields)

        schema = self.filter_required_fields(OPENING_SENSOR_JSONSCHEMA, skip_require_fields)
        self.validate_config(config, schema)

        self._storage_max_age = config.get(CONFKEY_STORAGE_MAX_AGE_SECS, 60)

        storage_file = config.get(CONFKEY_STORAGE_FILE)
        self._storage.set_file(storage_file)

        try:
            self._storage.load()
        except StorageException as ex:
            self._logger.exception(ex)

    def _determine_and_store_since(self, state_value: StateValue):
        success_value = StateValue.is_success(state_value)
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
        if value_since != state_value.value:
            value_since = state_value.value
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

    def _create_message(self,
                        state: StateValue,
                        since: Optional[datetime.datetime],
                        rssi: Optional[int],
                        timestamp: Optional[datetime.datetime] = None) -> Dict[str, any]:

        if not timestamp:
            timestamp = self._now()

        data = {
            JsonAttributes.DEVICE: self.name,
            JsonAttributes.STATUS: state.value,
            JsonAttributes.TIMESTAMP: timestamp,
        }
        if rssi:
            data[JsonAttributes.RSSI] = rssi
        if since is not None:
            data[JsonAttributes.SINCE] = since

        return data

    def check_cyclic_tasks(self):
        self._check_and_send_offline()

        if self._is_offline:
            self._determine_and_store_since(StateValue.OFFLINE)

    @classmethod
    def extract_state_value_from_f6_10_00(cls, data: Dict[str, any]) -> StateValue:
        value = data.get("WIN")
        if value == 3:
            return StateValue.CLOSED
        elif value == 2:
            return StateValue.OPEN
        elif value == 1:
            return StateValue.TILTED
        else:
            return StateValue.ERROR

    @classmethod
    def extract_state_value_from_d5_00_01(cls, data: Dict[str, any]) -> StateValue:
        value = data.get("CO")
        if value == 0:
            return StateValue.OPEN
        elif value == 1:
            return StateValue.CLOSED
        else:
            return StateValue.ERROR

    def process_enocean_message(self, message: EnoceanMessage):
        packet: RadioPacket = message.payload
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped non radio packet (packet_type=%s)", EnoceanTools.packet_type_to_string(packet.rorg))
            return

        eep_handler = next((e for e in self._eep_handlers if e.eep.rorg == packet.rorg), None)
        if not eep_handler:
            # Eltako FTKB is supposed to send a voltage and storage telegram (EEP 07-08-00),
            # but in reality it sends an unknown A5-?-? telegram, which does not make sense.
            # if self._logger.isEnabledFor(logging.DEBUG):
            #     self._logger.debug("skipped packet with rorg=%s\n%s", hex(packet.rorg), PickleTools.pickle_packet(packet))
            return

        packet_data = EnoceanTools.extract_packet_props(packet, eep_handler.eep)

        # fix for Eltako FTKB: skip equal/doubled packets which arrive within short time (usually 3.1s)
        now = self._now()
        if self._last_packet_time and self._last_packet_data:
            diff_seconds = (now - self._last_packet_time).total_seconds()
            if diff_seconds < self.ELTAKO_FTKB_DOUBLED_TIME:
                if self._last_packet_data == packet_data:
                    self._logger.debug("skipped doubled packet (%.1fs)!", diff_seconds)
                    return
        self._last_packet_data = packet_data
        self._last_packet_time = now

        self._reset_offline_refresh_timer()

        try:
            value = eep_handler.extract_state(packet_data)
        except DeviceException as ex:
            self._logger.exception(ex)
            value = StateValue.ERROR

        if value == StateValue.ERROR and self._logger.isEnabledFor(logging.DEBUG):
            if self._logger.isEnabledFor(logging.DEBUG):
                # write ascii representation to reproduce in tests
                self._logger.debug("proceed_enocean - pickled error packet:\n%s", PickleTools.pickle_packet(packet))

        since = self._determine_and_store_since(value)

        message_data = self._create_message(value, since, packet.dBm)
        self._publish_mqtt(message_data)

    def _restore_last_state(self):
        """restore old STATE when in time"""
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

        last_handle_value = StateValue.parse(last_value)
        if not StateValue.is_success(last_handle_value):
            return

        self._logger.info("old state '%s' (%s) restored.", last_handle_value, last_observation)
        message = self._create_message(last_handle_value, last_since, rssi=None, timestamp=last_observation)
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
