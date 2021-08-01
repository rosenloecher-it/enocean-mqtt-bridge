import json
from enum import Enum
from typing import Optional

import time

from src.config import Config
from src.common.json_attributes import JsonAttributes
from src.device.base.base_device import BaseDevice
from src.device.base.base_mqtt import BaseMqtt
from src.common.conf_device_key import ConfDeviceKey
from src.common.actor_command import ActorCommand
from src.device.device_exception import DeviceException
from src.device.misc.rocker_switch_tools import RockerSwitchTools, RockerPress, RockerButton, RockerAction
from src.common.switch_state import SwitchState


class RockerSwitchAction(Enum):
    ON = "on"  # press
    OFF = "off"  # press
    RELEASE = "release"


class BaseRockerActor(BaseDevice, BaseMqtt):
    """Base class for actors based on rocker switches (EEP f6-02-02)"""

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

    def _create_json_message(self, switch_state: SwitchState, dim_value: Optional[int], rssi: Optional[int] = None):
        data = {
            JsonAttributes.TIMESTAMP: self._now().isoformat(),
            JsonAttributes.STATE: switch_state.value
        }
        if rssi is not None:
            data[JsonAttributes.RSSI] = rssi
        if dim_value is not None:
            data[JsonAttributes.DIM_STATE] = dim_value

        json_text = json.dumps(data)
        return json_text

    def _create_switch_packet(self, switch_action, learn=False, destination=None):
        # simulate rocker switch
        if switch_action == RockerSwitchAction.ON:
            rocker_action = RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1)
        elif switch_action == RockerSwitchAction.OFF:
            switch_action = RockerPress.PRESS_SHORT
            rocker_action = RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK0)
        elif switch_action == RockerSwitchAction.RELEASE:
            rocker_action = RockerAction(RockerPress.RELEASE)
        else:
            raise RuntimeError()

        destination = destination or self._enocean_target or 0xffffffff

        return RockerSwitchTools.create_packet(
            rocker_action,
            destination=destination,
            sender=self._enocean_sender,
            learn=learn
        )

    def _execute_actor_command(self, command: ActorCommand, learn=False):
        destination = 0xffffffff

        if command in [ActorCommand.ON, ActorCommand.OFF]:
            action = RockerSwitchAction.ON if command == ActorCommand.ON else RockerSwitchAction.OFF
            packet = self._create_switch_packet(action, destination=destination, learn=learn)
            self._send_enocean_packet(packet)

            time.sleep(self._time_between_rocker_commands)

            packet = self._create_switch_packet(RockerSwitchAction.RELEASE, destination=destination)
            self._send_enocean_packet(packet)
        else:
            self._logger.info("command '{}' not supported!".format(command))

    def process_mqtt_message(self, message):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
        self._logger.debug('process_mqtt_message: "%s"', message.payload)

        try:
            command = ActorCommand.parse_switch(message.payload)
            self._logger.debug("command '{}'".format(command))
            self._execute_actor_command(command)
        except ValueError:
            self._logger.error("cannot execute command! message: {}".format(message.payload))
