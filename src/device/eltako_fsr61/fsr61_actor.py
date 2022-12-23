import json
import logging
import random
from datetime import datetime
from typing import Optional

from paho.mqtt.client import MQTTMessage

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket
from src.command.switch_command import SwitchCommand
from src.common.json_attributes import JsonAttributes
from src.common.switch_status import SwitchStatus
from src.device.base.cyclic_device import CheckCyclicTask
from src.device.base.scene_actor import SceneActor
from src.device.eltako_fsr61.fsr61_eep import Fsr61Eep, Fsr61Action, Fsr61Command
from src.device.rocker_switch.rocker_switch_tools import RockerSwitchTools, RockerButton
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class Fsr61Actor(SceneActor, CheckCyclicTask):
    """
    Specialized for: Eltako FSR61-230V (an ON/OFF relay switch)
    """

    DEFAULT_REFRESH_RATE = 300  # in seconds

    def __init__(self, name):
        SceneActor.__init__(self, name)
        CheckCyclicTask.__init__(self)

        self._current_switch_state: Optional[SwitchStatus] = None
        self._last_status_request: Optional[datetime] = None

    def process_enocean_message(self, message: EnoceanMessage):
        packet: RadioPacket = message.payload
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return

        if packet.rorg == RockerSwitchTools.DEFAULT_EEP.rorg:
            props = RockerSwitchTools.extract_props(packet)
            self._logger.debug("proceed_enocean - got=%s", props)
            action = RockerSwitchTools.extract_action(props)

            if action.button == RockerButton.ROCK3:
                self._current_switch_state = SwitchStatus.ON
            elif action.button == RockerButton.ROCK2:
                self._current_switch_state = SwitchStatus.OFF
            else:
                self._current_switch_state = SwitchStatus.ERROR
        else:
            self._current_switch_state = SwitchStatus.ERROR

        if self._current_switch_state not in [SwitchStatus.ON, SwitchStatus.OFF]:
            if self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug("proceed_enocean - pickled error packet:\n%s", PickleTools.pickle_packet(packet))

        self._logger.debug("proceed_enocean - switch_state=%s", self._current_switch_state)

        self._last_status_request = self._now()
        self._reset_offline_refresh_timer()

        message = self._create_json_message(self._current_switch_state)
        self._publish_mqtt(message)

    def _create_json_message(self, switch_state: SwitchStatus):
        data = {
            JsonAttributes.DEVICE: self.name,
            JsonAttributes.STATUS: switch_state.value,
            JsonAttributes.TIMESTAMP: self._now().isoformat(),
        }

        json_text = json.dumps(data, sort_keys=True)
        return json_text

    def process_mqtt_message(self, message: MQTTMessage):
        try:
            self._logger.debug('process_mqtt_message: "%s"', message.payload)
            command = SwitchCommand.parse(message.payload)
            self._logger.debug("mqtt command: '{}'".format(repr(command)))
            self._execute_actor_command(command)
        except ValueError:
            self._logger.error("cannot execute command! message: {}".format(message.payload))

    def _execute_actor_command(self, command: SwitchCommand):
        if command.is_toggle:
            command = SwitchCommand.OFF if self._current_switch_state == SwitchStatus.ON else SwitchCommand.ON

        if command.is_on_or_off:
            action = Fsr61Action(
                command=Fsr61Command.SWITCHING,
                switch_state=SwitchStatus.ON if command.is_on else SwitchStatus.OFF,
            )
        elif command.is_update:
            action = Fsr61Action(command=Fsr61Command.STATUS_REQUEST)
        elif command.is_learn:
            action = Fsr61Action(command=Fsr61Command.SWITCHING, switch_state=SwitchStatus.ON, learn=True)
        else:
            raise ValueError("SwitchCommand ({}) not supported!".format(command))

        action.sender = self._enocean_sender
        action.destination = self._enocean_target or 0xffffffff

        props, packet = Fsr61Eep.create_props_and_packet(action)
        self._logger.debug("sending '{}' => {}".format(action, props))
        self._send_enocean_packet(packet)

    def check_cyclic_tasks(self):
        self._check_and_send_offline()
        self._request_update()

    def _request_update(self):
        diff_seconds = None
        now = self._now()
        refresh_rate = self._randomized_refresh_rate

        if self._last_status_request is not None:
            diff_seconds = (now - self._last_status_request).total_seconds()

        if diff_seconds is None or diff_seconds >= refresh_rate:
            self._last_status_request = now
            self._execute_actor_command(SwitchCommand.UPDATE)

    @property
    def _randomized_refresh_rate(self) -> int:
        return self.DEFAULT_REFRESH_RATE + random.randint(0, self.DEFAULT_REFRESH_RATE * 0.1)
