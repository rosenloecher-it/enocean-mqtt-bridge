from enum import Enum
from typing import Optional, Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.conf_device_key import ConfDeviceKey
from src.device.rocker_actor import RockerActor, StateValue, ActorCommand
from src.enocean_connector import EnoceanMessage
from src.storage import Storage, StorageException
from src.tools.device_exception import DeviceException
from src.tools.enocean_tools import EnoceanTools
from src.tools.fud61_tools import Fud61Tools
from src.tools.rocker_switch_tools import RockerSwitchTools


class Fud61SwitchAction(Enum):
    ON = "on"
    OFF = "off"
    AUTO = "auto"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)

    @classmethod
    def parse(cls, text):
        text = str(text).lower().strip()
        for e in cls:
            if text == e.value:
                return e
        return None


class StorageKey(Enum):
    VALUE = "VALUE"
    LAST_UPDATE = "LAST_UPDATE"


class Fud61SimpleSwitch(RockerActor):
    """
    Serve as as
    """

    def __init__(self, name):
        super().__init__(name)

        # base target is Fud61
        self._eep = Fud61Tools.DEFAULT_EEP.clone()

        # 2. profile for rocker switch
        self._switch_eep = RockerSwitchTools.DEFAULT_EEP.clone()

        # self._enocean_target  == dimmer
        self._enocean_target_switch = None

        self._target_state = False
        self._switch_channels = {}  # type: Dict[int, Fud61SwitchAction]

        self._storage = Storage()

    @property
    def enocean_targets(self):
        # get notification for dimmer and  switch
        return [self._enocean_target, self._enocean_target_switch]

    def set_config(self, config):
        BaseDevice.set_config(self, config)

        key = ConfDeviceKey.ENOCEAN_TARGET_SWITCH
        self._enocean_target_switch = Config.get_int(config, key, None)
        if not self._enocean_target_switch:
            message = self.MISSING_CONFIG_FOR_NAME.format(key.enum, self._name)
            self._logger.error(message)
            raise DeviceException(message)

        items = [
            (ConfDeviceKey.ROCKER_BUTTON_0, 0),
            (ConfDeviceKey.ROCKER_BUTTON_1, 1),
            (ConfDeviceKey.ROCKER_BUTTON_2, 2),
            (ConfDeviceKey.ROCKER_BUTTON_3, 3),
        ]
        for key, index in items:
            text = Config.get_str(config, key)
            action = Fud61SwitchAction.parse(text)
            if action:
                self._switch_channels[index] = action

        storage_file = Config.get_str(config, ConfDeviceKey.STORAGE_FILE, None)
        self._storage.set_file(storage_file)

        try:
            self._storage.load()
            self._target_state = bool(self._storage.get(StorageKey.VALUE.value))
        except StorageException as ex:
            self._logger.exception(ex)
            self._target_state = False

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return

        if message.enocean_id == self._enocean_target:  # fud61
            self._process_dimmer_message(message)
        elif message.enocean_id == self._enocean_target_switch:  # rocker switch
            self._process_switch_message(message)

    def _process_dimmer_message(self, message: EnoceanMessage):
        packet = message.payload  # type: Packet
        if packet.rorg != self._eep.rorg:
            self._logger.debug("skipped fud61 packet with rorg=%s", hex(packet.rorg))
            return

        data = Fud61Tools.extract_props(packet)
        message = Fud61Tools.extract_message(data)
        self._logger.info("process dimmer message: %s => %s", data, message)

        self._set_target_state(message.switch_state == StateValue.ON)

    def _process_switch_message(self, message: EnoceanMessage):
        packet = message.payload  # type: Packet
        if packet.rorg != self._switch_eep.rorg:
            self._logger.warning("skipped rocker switch packet with rorg=%s", hex(packet.rorg))
            return

        data = EnoceanTools.extract_props(packet, self._switch_eep)
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 1, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 1, 'R2': 3, 'SA': 1, 'T21': 1, 'NU': 1}"
        # "{'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}"

        pressed_switch = None  # type: Optional[int]
        if data["SA"] == 1:
            pressed_switch = data["R2"]
        elif data["EB"] == 1:
            pressed_switch = data["R1"]

        action = self._switch_channels.get(pressed_switch)
        target_state = None  # Optional[bool]
        if action == Fud61SwitchAction.AUTO:
            target_state = not self._target_state
        elif action == Fud61SwitchAction.ON:
            target_state = True
        elif action == Fud61SwitchAction.OFF:
            target_state = False

        if target_state is not None:
            self._logger.info("process switch message - switch=%s, action=%s, target_state=%s",
                              pressed_switch, action, target_state)
            self._set_target_state(target_state)

            command = ActorCommand.ON if self._target_state else ActorCommand.OFF
            self._execute_actor_command(command)

    def _set_target_state(self, target_state: bool) -> bool:
        self._target_state = bool(target_state)
        self._storage.set(StorageKey.VALUE.value, self._target_state)
        self._storage.set(StorageKey.LAST_UPDATE.value, self._now())

        try:
            self._storage.save()
        except StorageException as ex:
            self._logger.exception(ex)

        return self._target_state
