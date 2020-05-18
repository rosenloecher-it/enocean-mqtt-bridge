import json
from enum import Enum
from typing import Optional

import time

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.base_mqtt import BaseMqtt
from src.device.conf_device_key import ConfDeviceKey
from src.device.device_exception import DeviceException
from src.device.rocker_switch import RockerSwitch, RockerAction, RockerButton


class SwitchAction(Enum):
    ON = "on"  # press
    OFF = "off"  # press
    RELEASE = "release"


class ActorCommand(Enum):
    ON = "on"
    OFF = "off"
    UPDATE = "update"  # trigger updated notification


class StateValue(Enum):
    ERROR = "ERROR"
    OFF = "OFF"
    ON = "ON"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)

    @classmethod
    def is_success(cls, state):
        return state in [cls.OFF, cls.ON]


class OutputAttributes(Enum):
    RSSI = "RSSI"
    TIMESTAMP = "TIMESTAMP"
    STATE = "STATE"
    DIM = "DIM"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


class RockerActor(BaseDevice, BaseMqtt):
    """Base class for actor based on rocker switches (eep f6-02-02)"""

    def __init__(self, name):
        BaseDevice.__init__(self, name)
        BaseMqtt.__init__(self)

        self._mqtt_channel_cmd = None

        self._time_between_rocker_commands = 0.05

    def set_config(self, config):
        BaseDevice.set_config(self, config)
        BaseMqtt.set_config(self, config)

        key = ConfDeviceKey.MQTT_CHANNEL_CMD
        self._mqtt_channel_cmd = Config.get_str(config, key)
        if not self._mqtt_channel_cmd:
            message = self.MISSING_CONFIG_FOR_NAME.format(key.value, self._name)
            self._logger.error(message)
            raise DeviceException(message)

    def get_mqtt_channel_subscriptions(self):
        """signal ensor state, outbound channel"""
        return [self._mqtt_channel_cmd]

    def _create_message(self, switch_state: StateValue, dim_state: Optional[int], rssi: Optional[int] = None):
        data = {
            OutputAttributes.TIMESTAMP.value: self._now().isoformat(),
            OutputAttributes.STATE.value: switch_state.value
        }
        if rssi is not None:
            data[OutputAttributes.RSSI.value] = rssi
        if dim_state is not None:
            data[OutputAttributes.DIM.value] = dim_state

        json_text = json.dumps(data)
        return json_text

    def _create_switch_packet(self, action, learn=False, destination=None):
        # simulate rocker switch
        if action == SwitchAction.ON:
            action = RockerAction.PRESS_SHORT
            button = RockerButton.ROCK1
        elif action == SwitchAction.OFF:
            action = RockerAction.PRESS_SHORT
            button = RockerButton.ROCK0
        elif action == SwitchAction.RELEASE:
            action = RockerAction.RELEASE
            button = None
        else:
            raise RuntimeError()

        destination = destination or self._enocean_target or 0xffffffff

        return RockerSwitch.simu_packet(
            action, button,
            destination=destination,
            sender=self._enocean_sender,
            learn=learn
        )

    def _execute_actor_command(self, command: ActorCommand, learn=False):
        destination = 0xffffffff

        if command in [ActorCommand.ON, ActorCommand.OFF]:
            action = SwitchAction.ON if command == ActorCommand.ON else SwitchAction.OFF
            packet = self._create_switch_packet(action, destination=destination, learn=learn)
            self._send_enocean_packet(packet)

            time.sleep(self._time_between_rocker_commands)

            packet = self._create_switch_packet(SwitchAction.RELEASE, destination=destination)
            self._send_enocean_packet(packet)
        elif command == ActorCommand.UPDATE:
            self._logger.info("command 'UPDATE' not supported!")

    @classmethod
    def extract_actor_command(cls, text: str, recusive=True) -> ActorCommand:
        if text:
            comp = str(text).upper().strip()
            if comp in ["ON", "1", "100"]:
                return ActorCommand.ON
            elif comp in ["OFF", "0"]:
                return ActorCommand.OFF
            elif comp == "UPDATE":
                return ActorCommand.UPDATE
            elif recusive and comp[0] == "{":  # {"STATE": "off"}
                data = json.loads(text)
                value = data.get(OutputAttributes.STATE.value)
                return cls.extract_actor_command(value, recusive=False)

        raise ValueError()

    def process_mqtt_message(self, message):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
        self._logger.debug('process_mqtt_message: "%s"', message.payload)

        payload = message.payload
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        try:
            command = self.extract_actor_command(payload)
            self._logger.debug("command '{}'".format(command.value))
            self._execute_actor_command(command)
        except ValueError:
            self._logger.error("cannot execute command! message: {}".format(payload))
