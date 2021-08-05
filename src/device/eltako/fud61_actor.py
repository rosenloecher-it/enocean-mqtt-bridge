import json
import logging
import random
from datetime import datetime
from typing import Dict

from paho.mqtt.client import MQTTMessage
from tzlocal import get_localzone

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket
from src.command.dimmer_command import DimmerCommand, DimmerCommandType
from src.common.conf_device_key import ConfDeviceKey
from src.common.json_attributes import JsonAttributes
from src.config import Config
from src.device.base.base_cyclic import BaseCyclic
from src.device.base.base_device import BaseDevice
from src.device.base.base_mqtt import BaseMqtt
from src.device.base.base_rocker_actor import SwitchState
from src.device.device_exception import DeviceException
from src.device.eltako.fud61_eep import Fud61Eep, Fud61Action, Fud61Command
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class Fud61Actor(BaseDevice, BaseMqtt, BaseCyclic):
    """
    Specialized for: Eltako FUD61NP(N)-230V (dimmer)

    EEP: A5-38-08 (RORG 0xA5 - FUNC 0x38 - TYPE 0x08 - Gateway)
        shortcut 	description 	            values
        COM 	    Command ID 	                0-13 - Command ID
        EDIM 	    Dimming value               absolute [0...255]
                                                relative [0...100])
        RMP 	    Ramping time in seconds     0 = no ramping,
                                                1...255 = seconds to 100%
        EDIMR 	    Dimming Range 	            0 - Absolute value
                                                1 - Relative value
        STR 	    Store final value 	enum 	0 - No
                                                1 - Yes
        SW 	        Switching command 	        0 - Off
                                                1 - On

    See also:
    - https://www.eltako.com/fileadmin/downloads/de/Gesamtkatalog/Eltako_Gesamtkatalog_KapT_low_res.pdf
    - https://github.com/kipe/enocean/blob/master/SUPPORTED_PROFILES.md
    """

    DEFAULT_REFRESH_RATE = 300  # in seconds

    MIN_DIM_STATE = 10

    def __init__(self, name):
        BaseDevice.__init__(self, name)
        BaseMqtt.__init__(self)
        BaseCyclic.__init__(self)

        self._mqtt_channel_cmd = None

        self._default_dim_state = Fud61Eep.DEFAULT_DIM_STATE
        self._last_dim_state = Fud61Eep.DEFAULT_DIM_STATE
        self._current_switch_state = None  # type: SwitchState

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

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload  # type: RadioPacket
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return

        self._process_actor_packet(packet)

    def _process_actor_packet(self, packet: RadioPacket):
        if packet.rorg == 0xf6:
            return  # unknown telegramm, not used

        props = Fud61Eep.get_props_from_packet(packet)  # type: Dict
        self._logger.debug("process actor message: %s", props)
        action = Fud61Eep.get_action_from_props(props)  # type: Fud61Action

        if action.switch_state not in [SwitchState.ON, SwitchState.OFF] or action.dim_state is None:
            if self._logger.isEnabledFor(logging.DEBUG):
                # write ascii representation to reproduce in tests
                self._logger.debug("proceed_enocean - pickled error packet:\n%s", PickleTools.pickle_packet(packet))

        self._current_switch_state = action.switch_state
        if isinstance(action.dim_state, int) and action.dim_state > self.MIN_DIM_STATE:
            self._last_dim_state = action.dim_state

        self._reset_offline_message_counter()
        self._last_status_request = self._now()

        self._publish_actor_result(action, packet.dBm)

    def _publish_actor_result(self, action: Fud61Action, rssi: int):
        message = self._create_json_message(action.switch_state, action.dim_state, rssi=rssi)
        self._publish_mqtt(message)

    def get_teach_print_message(self):
        return "FUD61: Set teach target to AUTO!"

    def send_teach_telegram(self, cli_arg):
        self._execute_actor_command(DimmerCommand(DimmerCommandType.LEARN))

    def get_mqtt_channel_subscriptions(self):
        """signal ensor state, outbound channel"""
        return [self._mqtt_channel_cmd]

    def _create_json_message(self, switch_state: SwitchState, dim_state: int, rssi: int):
        data = {
            JsonAttributes.TIMESTAMP: self._now().isoformat(),
            JsonAttributes.STATE: switch_state.value,
            JsonAttributes.DIM_STATE: dim_state
        }
        if rssi is not None:
            data["rssi"] = rssi

        json_text = json.dumps(data)
        return json_text

    def process_mqtt_message(self, message: MQTTMessage):
        try:
            self._logger.debug('process_mqtt_message: "%s"', message.payload)
            command = DimmerCommand.parse(message.payload)
            self._logger.debug("mqtt command: '{}'".format(repr(command)))
            self._execute_actor_command(command)
        except ValueError:
            self._logger.error("cannot execute command! message: {}".format(message.payload))

    def _execute_actor_command(self, command: DimmerCommand):
        action, props, packet = None, None, None

        if command.is_on:
            action = Fud61Action(
                command=Fud61Command.DIMMING,
                switch_state=SwitchState.ON,
                dim_state=self._last_dim_state
            )
        elif command.is_off:
            action = Fud61Action(
                command=Fud61Command.DIMMING,
                switch_state=SwitchState.OFF
            )
        elif command.is_dim:
            action = Fud61Action(
                command=Fud61Command.DIMMING,
                # switch_state=SwitchState.ON if dim_state > 0 else SwitchState.OFF,
                dim_state=command.value
            )
        elif command.is_update:
            action = Fud61Action(command=Fud61Command.STATUS_REQUEST)
        elif command.is_learn:
            action = Fud61Action(command=Fud61Command.DIMMING, dim_state=100, learn=True)
        else:
            raise ValueError("command ({}) is not supported!".format(repr(command)))

        action.sender = self._enocean_sender
        action.destination = self._enocean_target or 0xffffffff

        props, packet = Fud61Eep.create_props_and_packet(action)
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
            self._execute_actor_command(DimmerCommand(DimmerCommandType.UPDATE))

    @property
    def _randomized_refresh_rate(self) -> int:
        return self.DEFAULT_REFRESH_RATE + random.randint(0, self.DEFAULT_REFRESH_RATE * 0.1)

    def _now(self):
        """overwrite in test to simulate different times"""
        return datetime.now(tz=get_localzone())
