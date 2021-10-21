import json
import random
from datetime import datetime
from enum import Enum
from math import isclose
from typing import List, Optional

from paho.mqtt.client import MQTTMessage
from tzlocal import get_localzone

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket
from src.command.shutter_command import ShutterCommand, ShutterCommandType
from src.common.json_attributes import JsonAttributes
from src.device.base.cyclic_device import CheckCyclicTask
from src.device.base.scene_actor import SceneActor
from src.device.device_exception import DeviceException
from src.device.eltako.fsb61_eep import Fsb61StatusConverter, Fsb61Command, Fsb61CommandType, Fsb61CommandConverter, \
    Fsb61StatusType, Fsb61Status
from src.device.eltako.fsb61_shutter_position import Fsb61ShutterPosition, Fsb61ShutterState
from src.device.eltako.fsb61_storage import Fsb61Storage
from src.enocean_connector import EnoceanMessage
from src.storage import CONFKEY_STORAGE_FILE, CONFKEY_STORAGE_MAX_AGE_SECS
from src.tools.enocean_tools import EnoceanTools

CONFKEY_TIME_UP_ROLLING = "time_up_rolling"
CONFKEY_TIME_UP_DRIVING = "time_up_driving"
CONFKEY_TIME_DOWN_ROLLING = "time_down_rolling"
CONFKEY_TIME_DOWN_DRIVING = "time_down_driving"


FSB61_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_STORAGE_FILE: {"type": "string", "minLength": 1},
        CONFKEY_STORAGE_MAX_AGE_SECS: {"type": "number", "minimum": 1},

        CONFKEY_TIME_DOWN_DRIVING: {"type": "number", "minimum": 1, "maximum": 149.9},
        CONFKEY_TIME_DOWN_ROLLING: {"type": "number", "minimum": 1, "maximum": 149.9},
        CONFKEY_TIME_UP_DRIVING: {"type": "number", "minimum": 1, "maximum": 149.9},
        CONFKEY_TIME_UP_ROLLING: {"type": "number", "minimum": 1, "maximum": 149.9},
    },
    "required": [
        CONFKEY_STORAGE_FILE,
        CONFKEY_TIME_DOWN_DRIVING,
        CONFKEY_TIME_DOWN_ROLLING,
        CONFKEY_TIME_UP_DRIVING,
        CONFKEY_TIME_UP_ROLLING,
    ],
}


class Fsb61State(Enum):
    OFFLINE = "offline"
    READY = "ready"
    NOT_CALIBRATED = "not-calibrated"
    ERROR = "error"


class Fsb61Actor(SceneActor, CheckCyclicTask):
    """
    Specialized for: Eltako FSB61NB-230V
    """

    DEFAULT_REFRESH_RATE = 300  # in seconds
    DEFAULT_SEQUENCE_DELAY = 0.1
    ROLLING_POS = 90.0  # 90 - 100%, within this range the position is interpreted as shutter gaps only
    POSITION_RESERVE_TIME = 2.0
    CALIBRATION_AFTER_JUMPS = 7

    def __init__(self, name):
        SceneActor.__init__(self, name)
        CheckCyclicTask.__init__(self)

        self._last_status_request_time = None  # type: Optional[datetime]

        self._storage = Fsb61Storage(name)

        self._shutter_position = Fsb61ShutterPosition(name)
        self._shutter_position.jumps_without_calibration = self.CALIBRATION_AFTER_JUMPS

        self._stored_device_commands = None  # type: Optional[List[Fsb61Command]]
        self._stored_device_commands_time = None  # type Optional[datetime]

    def _set_config(self, config, skip_require_fields: [str]):
        super()._set_config(config, skip_require_fields)

        self.validate_config(config, FSB61_JSONSCHEMA)

        self._shutter_position.time_down_driving = config[CONFKEY_TIME_DOWN_DRIVING]
        self._shutter_position.time_down_rolling = config[CONFKEY_TIME_DOWN_ROLLING]
        self._shutter_position.time_up_driving = config[CONFKEY_TIME_UP_DRIVING]
        self._shutter_position.time_up_rolling = config[CONFKEY_TIME_UP_ROLLING]

        self._storage.set_file(config[CONFKEY_STORAGE_FILE])
        self._storage.storage_max_age = config.get(CONFKEY_STORAGE_MAX_AGE_SECS, 60 * 60)
        self._storage.restore(self._now())

        self._shutter_position.value = self._storage.value

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload  # type: RadioPacket

        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return

        rocker_scene = self.find_rocker_scene(packet)
        if rocker_scene:
            self._reset_stored_device_commands()
            self.process_rocker_scene(rocker_scene)
        else:
            self.process_enocean_fsb61_message(message)

    def process_enocean_fsb61_message(self, message: EnoceanMessage):
        packet = message.payload  # type: RadioPacket

        try:
            packet.parse()
            status = Fsb61StatusConverter.extract_packet(packet)
        except Exception as ex:
            self._logger.exception(ex)
            EnoceanTools.log_pickled_enocean_packet(self._logger.error, packet, "process_enocean_fsb61_message - {}".format(str(ex)))
            return

        if status.type == Fsb61StatusType.UNKNOWN:
            EnoceanTools.log_pickled_enocean_packet(self._logger.warning, packet, "process_enocean_fsb61_message - unknown packet type")
            return

        # # DEBUG
        # EnoceanTools.log_pickled_enocean_packet(self._logger.debug, packet, 'process_enocean_fsb61_message')

        self._shutter_position.update(status)
        self._storage.save_value(self._shutter_position.value, self._now())

        self._logger.debug("process_enocean_message: %s", status)

        self._publish_actor_result()

        self._process_device_command2(status)  # trigger queued commands

        # prevent offline message
        self._reset_offline_refresh_timer()
        self._last_status_request_time = self._now()

    def _publish_actor_result(self):
        state = Fsb61State.READY if self._shutter_position.state == Fsb61ShutterState.READY else Fsb61State.NOT_CALIBRATED
        message = self._create_json_message(state, self._storage.value, self._storage.since)
        self._publish_mqtt(message)

    def _create_json_message(self, state: Fsb61State, position: Optional[float], since: Optional[datetime]):
        data = {
            JsonAttributes.TIMESTAMP: self._now().isoformat(),
            JsonAttributes.STATE: state.value,
        }
        if position is not None:
            data[JsonAttributes.VALUE] = int(round(position))
        if since is not None:
            data[JsonAttributes.SINCE] = since.isoformat()

        json_text = json.dumps(data)
        return json_text

    def process_mqtt_message(self, message: MQTTMessage):
        try:
            shutter_command = ShutterCommand.parse(message.payload)
            self._logger.debug('process_mqtt_message: "%s" => %s', message.payload, repr(shutter_command))

            device_commands = self.create_device_commands(shutter_command)
            if device_commands:
                self._process_device_command1(device_commands)

        except ValueError as ex:
            self._logger.error("cannot execute command ({})! message: {}".format(ex, message.payload))

    def _process_device_command1(self, device_commands: List[Fsb61Command]):
        device_command1 = device_commands[0]
        packet = Fsb61CommandConverter.create_packet(device_command1)
        self._send_enocean_packet(packet)

        self._logger.debug('_process_device_command1: "%s"', device_commands)

        if len(device_commands) == 2:
            self._stored_device_commands = device_commands
            self._stored_device_commands_time = self._now()
        elif len(device_commands) > 3:
            raise DeviceException("Invalid command sequence (len > 2)!")

    def _process_device_command2(self, change: Fsb61Status):
        """
        """
        if change.type not in [Fsb61StatusType.OPENED, Fsb61StatusType.CLOSED]:
            return

        # self._logger.info("_process_device_command2 - change: %s, stored: %s", change, self._device_commands)

        while True:
            if not self._stored_device_commands and self._stored_device_commands_time is None:
                break
            if not self._stored_device_commands or len(self._stored_device_commands) != 2 or not self._stored_device_commands_time:
                raise DeviceException("Invalid command sequence data!")

            device_command1 = self._stored_device_commands[0]

            if change.type == Fsb61StatusType.OPENED and device_command1.type == Fsb61CommandType.OPEN \
                    and change.type == Fsb61StatusType.CLOSED and device_command1.type == Fsb61CommandType.CLOSE:
                self._logger.info(
                    "_process_device_command2 - wrong directions, abort 2. operation - change: %s; command: %s",
                    change.type, device_command1.type
                )
                break

            command_time = device_command1.time
            elapsed_time = (self._now() - self._stored_device_commands_time).total_seconds()
            driven_time = change.time
            tolerance = max(command_time * 0.1, 1.0)

            if not isclose(command_time, driven_time, abs_tol=tolerance) or not isclose(command_time, elapsed_time, abs_tol=tolerance):
                self._logger.info(
                    "_process_device_command2 - times differ, abort 2. operation - elapsed_time: %s; command_time: %s; driven_time: %s",
                    elapsed_time, command_time, driven_time
                )
                break

            device_command2 = self._stored_device_commands[1]
            self._logger.debug('_process_device_command2: "%s"', device_command2)
            packet = Fsb61CommandConverter.create_packet(device_command2)
            self._send_enocean_packet(packet)

            break

        self._reset_stored_device_commands()

    def _reset_stored_device_commands(self):
        self._stored_device_commands = None
        self._stored_device_commands_time = None

    def create_device_commands(self, order: ShutterCommand) -> List[Fsb61Command]:
        device_commands = []  # type: List[Fsb61Command]

        def create_action(cmd_type: Optional[Fsb61CommandType]):
            action = Fsb61Command(type=cmd_type)
            action.sender = self._enocean_sender
            action.destination = self._enocean_target or 0xffffffff
            return action

        def append_device_command(order_to_log, device_command_to_check):
            if device_command_to_check.time is not None and device_command_to_check.time <= 0.1:
                self._logger.info("Command (%s) skipped. Time (%.1f) to short.", order_to_log, device_command.time)
                return
            device_commands.append(device_command_to_check)

        if order.type == ShutterCommandType.LEARN:
            device_commands.append(create_action(Fsb61CommandType.LEARN))
        elif order.type == ShutterCommandType.UPDATE:
            device_commands.append(create_action(Fsb61CommandType.STATUS_REQUEST))
        elif order.type == ShutterCommandType.STOP:
            device_commands.append(create_action(Fsb61CommandType.STOP))

        elif order.type == ShutterCommandType.POSITION:
            value = order.value
            try:
                value = float(value)  # auto convert hex
            except ValueError:
                raise ValueError("cannot parse shutter position value ({}) as int!".format(value))
            if value is None or value < 0 or value > 100:
                raise ValueError("wrong shutter value ({}; expected: 0-100)!".format(value))

            if value == 0:
                device_command = create_action(Fsb61CommandType.OPEN)
                device_command.time = self._shutter_position.calc_seek_time(100, 0) + self.POSITION_RESERVE_TIME
                append_device_command(order, device_command)
            elif value == 100:
                device_command = create_action(Fsb61CommandType.CLOSE)
                device_command.time = self._shutter_position.calc_seek_time(0, 100) + self.POSITION_RESERVE_TIME
                append_device_command(order, device_command)

            elif not order.force_calibration and self._shutter_position.jumps_without_calibration < self.CALIBRATION_AFTER_JUMPS and \
                    self._shutter_position.state == Fsb61ShutterState.READY:

                command_type = Fsb61CommandType.CLOSE if value > self._shutter_position.value else Fsb61CommandType.OPEN
                device_command = create_action(command_type)
                device_command.time = self._shutter_position.calc_seek_time(self._shutter_position.value, value)
                append_device_command(order, device_command)

            else:  # with calibration
                if value > 65 or value >= self.ROLLING_POS:  # more closed than open
                    device_command = create_action(Fsb61CommandType.CLOSE)
                    device_command.time = self._shutter_position.calc_seek_time(0, 100) + self.POSITION_RESERVE_TIME
                    append_device_command(order, device_command)

                    device_command = create_action(Fsb61CommandType.OPEN)  # 2.
                    device_command.time = self._shutter_position.calc_seek_time(100, value)
                    append_device_command(order, device_command)

                else:  # more open than closed
                    device_command = create_action(Fsb61CommandType.OPEN)
                    device_command.time = self._shutter_position.calc_seek_time(100, 0) + self.POSITION_RESERVE_TIME
                    device_commands.append(device_command)

                    device_command = create_action(Fsb61CommandType.CLOSE)  # 2.
                    device_command.time = self._shutter_position.calc_seek_time(0, value)
                    append_device_command(order, device_command)

        return device_commands

    def open_mqtt(self):
        super().open_mqtt()

        # if self._storage.last_value() is not None:
        #     self._logger.info("old state '%s' (%s) restored.", last_handle_value, last_observation)
        #     message = self._create_message(last_handle_value, last_since, timestamp=last_observation)
        #     self._publish_mqtt(message)

    def close_mqtt(self):
        super().close_mqtt()

        self._storage.save_touched(self._now())

    def check_cyclic_tasks(self):
        self._check_and_send_offline()
        self._request_update()

    def _request_update(self):
        now = self._now()
        refresh_rate = self._randomized_refresh_rate

        request_time = self._last_status_request_time
        last_status_request_before = (now - request_time).total_seconds() if request_time is not None else None

        if last_status_request_before is None or last_status_request_before >= refresh_rate:
            self._last_status_request_time = now
            device_commands = self.create_device_commands(ShutterCommand(ShutterCommandType.UPDATE))
            self._process_device_command1(device_commands)

    @property
    def _randomized_refresh_rate(self) -> int:
        return self.DEFAULT_REFRESH_RATE + random.randint(0, self.DEFAULT_REFRESH_RATE * 0.1)

    def _now(self):
        """overwrite in test to simulate different times"""
        return datetime.now(tz=get_localzone())
