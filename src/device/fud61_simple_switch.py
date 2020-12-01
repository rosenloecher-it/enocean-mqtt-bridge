from enum import Enum
from typing import Dict

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet, RadioPacket

from src.common.conf_device_key import ConfDeviceKey
from src.config import Config
from src.device.base_cyclic import BaseCyclic
from src.device.base_device import BaseDevice
from src.device.base_rocker_actor import SwitchState, ActorCommand
from src.device.device_exception import DeviceException
from src.device.fud61_actor import Fud61Actor
from src.device.fud61_eep import Fud61Action
from src.device.rocker_switch_tools import RockerSwitchTools, RockerAction
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools


class Fud61SwitchOperation(Enum):
    ON = "on"
    OFF = "off"
    AUTO = "auto"

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, str(self))

    @classmethod
    def parse(cls, text):
        text = str(text).lower().strip()
        for e in cls:
            if text == e.value:
                return e
        return None


class Fud61SimpleSwitch(Fud61Actor):
    """
    Connects a rocker switch as an ON/OFF (only! == without dimming) switch to an Eltako FUD61NP(N).

    If you teach in rocker switches directly to an Eltako FUD61NP(N), the switches are used to dim the dimmer too, which
    means all real manual button presses must be timed more or less precisly to NOT trigger the dimming. My 4 year old
    daughter does not get this right always.

    There is no MQTT connection involved. This "bridge device" just triggers the ON/OFF telegrams directly to the FUD61.
    """

    def __init__(self, name):
        super().__init__(name)

        # self._enocean_target  == dimmer
        self._enocean_target_switch = None

        self._button_operations = {}  # type: Dict[int, Fud61SwitchOperation]

    @property
    def enocean_targets(self):
        # get notification for dimmer and  switch
        return [self._enocean_target, self._enocean_target_switch]

    def set_config(self, config):
        # completely overwrite base function to get rid of ConfDeviceKey.MQTT_CHANNEL_CMD
        BaseDevice.set_config(self, config)
        # skip, not needed: BaseMqtt.set_config(self, config)
        BaseCyclic.set_config(self, config)

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
            action = Fud61SwitchOperation.parse(text)
            if action:
                self._button_operations[index] = action

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return

        if message.enocean_id == self._enocean_target:  # fud61
            self._process_actor_packet(packet)
        elif message.enocean_id == self._enocean_target_switch:  # rocker switch
            self._process_switch_packet(packet)

    def _publish_actor_result(self, action: Fud61Action, rssi: int):
        pass  # no mqtt used here

    def _process_switch_packet(self, packet: RadioPacket):
        rocker_action = RockerSwitchTools.extract_action_from_packet(packet)  # type: RockerAction
        if rocker_action.button is None:
            return  # skip, likely RELEASE

        operation = self._button_operations.get(rocker_action.button.value)
        command = None  # Optional[ActorCommand]
        if operation == Fud61SwitchOperation.AUTO:
            if self._current_switch_state is SwitchState.ON:
                command = ActorCommand.OFF
            elif self._current_switch_state is SwitchState.OFF:
                command = ActorCommand.ON
        elif operation == Fud61SwitchOperation.ON:
            command = ActorCommand.ON
        elif operation == Fud61SwitchOperation.OFF:
            command = ActorCommand.OFF

        if command is None:
            self._logger.debug("skip rocker action: %s", rocker_action)
            return

        self._logger.debug("process rocker action: %s => %s", rocker_action, operation)
        self._execute_actor_command(command)
