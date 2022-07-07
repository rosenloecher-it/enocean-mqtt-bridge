import json
import time
from enum import Enum
from typing import Optional

from src.command.switch_command import SwitchCommand
from src.common.json_attributes import JsonAttributes
from src.common.switch_status import SwitchStatus
from src.device.base.device import Device
from src.device.misc.rocker_switch_tools import RockerSwitchTools, RockerPress, RockerButton, RockerAction
from src.enocean_connector import EnoceanMessage


class RockerSwitchAction(Enum):
    ON = "on"  # press
    OFF = "off"  # press
    RELEASE = "release"


class RockerActor(Device):
    """Base class for actors who listen to rocker switches (EEP f6-02-02)."""

    def __init__(self, name):
        super().__init__(name)

        self._time_between_rocker_commands = 0.05

    # def _set_config(self, config, skip_require_fields: [str]):
    #     super()._set_config(config, skip_require_fields)

    def _create_json_message(self, switch_state: SwitchStatus, dim_value: Optional[int]):
        data = {
            JsonAttributes.DEVICE: self.name,
            JsonAttributes.STATUS: switch_state.value,
            JsonAttributes.TIMESTAMP: self._now().isoformat(),
        }
        if dim_value is not None:
            data[JsonAttributes.DIM_STATUS] = dim_value

        json_text = json.dumps(data, sort_keys=True)
        return json_text

    def _create_switch_packet(self, switch_action, learn=False, destination=None):
        # simulate rocker switch
        if switch_action == RockerSwitchAction.ON:
            rocker_action = RockerAction(RockerPress.PRESS_SHORT, RockerButton.ROCK1)
        elif switch_action == RockerSwitchAction.OFF:
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

    def _execute_actor_command(self, command: SwitchCommand, learn=False):
        destination = 0xffffffff

        if command.is_on_or_off:
            action = RockerSwitchAction.ON if command.is_on else RockerSwitchAction.OFF
            packet = self._create_switch_packet(action, destination=destination, learn=learn)
            self._send_enocean_packet(packet)

            time.sleep(self._time_between_rocker_commands)

            packet = self._create_switch_packet(RockerSwitchAction.RELEASE, destination=destination)
            self._send_enocean_packet(packet)
        else:
            self._logger.info("command '{}' not supported!".format(command))

    def process_mqtt_message(self, message: EnoceanMessage):
        self._logger.debug('process_mqtt_message: "%s"', message.payload)

        try:
            command = SwitchCommand.parse(message.payload)
            self._logger.debug("command '{}'".format(command))
            self._execute_actor_command(command)
        except ValueError:
            self._logger.error("cannot execute command! message: {}".format(message.payload))
