import json
import logging
import random
from datetime import datetime
from typing import Optional

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket
from paho.mqtt.client import MQTTMessage
from tzlocal import get_localzone

from src.common.actor_command import ActorCommand
from src.common.conf_device_key import ConfDeviceKey
from src.common.json_attributes import JsonAttributes
from src.common.switch_state import SwitchState
from src.config import Config
from src.device.base.base_cyclic import BaseCyclic
from src.device.base.base_device import BaseDevice
from src.device.base.base_mqtt import BaseMqtt
from src.device.device_exception import DeviceException
from src.device.eltako_fsr61_eep import Fsr61Eep, EltakoFsr61Action, EltakoFsr61Command
from src.device.misc.rocker_switch_tools import RockerSwitchTools, RockerAction, RockerButton
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class EltakoFsr61Actor(BaseDevice, BaseMqtt, BaseCyclic):
    """
    Specialized for: Eltako FSR61-230V (an ON/OFF relay switch)
    """

    DEFAULT_REFRESH_RATE = 300  # in seconds

    def __init__(self, name):
        BaseDevice.__init__(self, name)
        BaseMqtt.__init__(self)
        BaseCyclic.__init__(self)

        self._mqtt_channel_cmd = None

        self._last_status_request = None  # type: datetime

    def set_config(self, config):
        BaseDevice.set_config(self, config)
        BaseMqtt.set_config(self, config)
        BaseCyclic.set_config(self, config)

        key = ConfDeviceKey.MQTT_CHANNEL_CMD
        self._mqtt_channel_cmd = Config.get_str(config, key)
        if not self._mqtt_channel_cmd:
            message = self.MISSING_CONFIG_FOR_NAME.format(key.value, self._name)
            self._logger.error(message)
            raise DeviceException(message)

    def send_teach_telegram(self, cli_arg):
        self._execute_actor_command(ActorCommand.LEARN)

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload  # type: RadioPacket
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return

        if packet.rorg == RockerSwitchTools.DEFAULT_EEP.rorg:
            props = RockerSwitchTools.extract_props(packet)
            self._logger.debug("proceed_enocean - got=%s", props)
            action = RockerSwitchTools.extract_action(props)  # type: RockerAction
            # action = RockerSwitchTools.extract_action_from_packet(packet)  # type: RockerAction

            if action.button == RockerButton.ROCK3:
                switch_state = SwitchState.ON
            elif action.button == RockerButton.ROCK2:
                switch_state = SwitchState.OFF
            else:
                switch_state = SwitchState.ERROR
        else:
            switch_state = SwitchState.ERROR

        if switch_state not in [SwitchState.ON, SwitchState.OFF]:
            if self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug("proceed_enocean - pickled error packet:\n%s", PickleTools.pickle_packet(packet))

        self._logger.debug("proceed_enocean - switch_state=%s", switch_state)

        self._last_status_request = self._now()
        self._reset_offline_message_counter()

        message = self._create_json_message(switch_state, rssi=packet.dBm)
        self._publish_mqtt(message)

    def get_mqtt_channel_subscriptions(self):
        """signal ensor state, outbound channel"""
        return [self._mqtt_channel_cmd]

    def _create_json_message(self, switch_state: SwitchState, rssi: Optional[int] = None):
        data = {
            JsonAttributes.TIMESTAMP: self._now().isoformat(),
            JsonAttributes.STATE: switch_state.value
        }
        if rssi is not None:
            data["rssi"] = rssi

        json_text = json.dumps(data)
        return json_text

    def process_mqtt_message(self, message: MQTTMessage):
        try:
            self._logger.debug('process_mqtt_message: "%s"', message.payload)
            command = ActorCommand.parse_switch(message.payload)
            self._logger.debug("mqtt command: '{}'".format(repr(command)))
            self._execute_actor_command(command)
        except ValueError:
            self._logger.error("cannot execute command! message: {}".format(message.payload))

    def _execute_actor_command(self, command: ActorCommand):
        if command in [ActorCommand.ON, ActorCommand.OFF]:
            action = EltakoFsr61Action(
                command=EltakoFsr61Command.SWITCHING,
                switch_state=SwitchState.ON if command == ActorCommand.ON else SwitchState.OFF,
            )
        elif command == ActorCommand.UPDATE:
            action = EltakoFsr61Action(command=EltakoFsr61Command.STATUS_REQUEST)
        elif command == ActorCommand.LEARN:
            action = EltakoFsr61Action(command=EltakoFsr61Command.SWITCHING, switch_state=SwitchState.ON, learn=True)
        else:
            raise ValueError("ActorCommand ({}) not supported!".format(command))

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
            self._execute_actor_command(ActorCommand.UPDATE)

    @property
    def _randomized_refresh_rate(self) -> int:
        return self.DEFAULT_REFRESH_RATE + random.randint(0, self.DEFAULT_REFRESH_RATE * 0.1)

    def _now(self):
        """overwrite in test to simulate different times"""
        return datetime.now(tz=get_localzone())
