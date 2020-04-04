import json
import logging
import time
from enum import Enum
from typing import Optional

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet, RadioPacket

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.conf_device_key import ConfDeviceKey
from src.enocean_connector import EnoceanMessage
from src.storage import Storage, StorageException
from src.tools import Tools


class SwitchAction(Enum):
    ON = "on"  # press
    OFF = "off"  # press
    RELEASE = "release"


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


class Fud61OutAttr(Enum):
    RSSI = "RSSI"
    TIMESTAMP = "TIMESTAMP"
    STATE = "STATE"
    DIM = "DIM"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


class Fud61Device(BaseDevice):
    """

    RORG 0xA5 - FUNC 0x38 - TYPE 0x08 - Gateway
    (https://github.com/kipe/enocean/blob/master/SUPPORTED_PROFILES.md)

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

    see also: https://www.eltako.com/fileadmin/downloads/de/Gesamtkatalog/Eltako_Gesamtkatalog_KapT_low_res.pdf

    """

    def __init__(self, name):
        super().__init__(name)

        # default config values
        self._enocean_rorg = 0xa5
        self._enocean_func = 0x38
        self._enocean_type = 0x08
        self._enocean_command = 0x02

        # simulate rocker switch
        self._switch_rorg = 0xf6
        self._switch_func = 0x02
        self._switch_type = 0x02
        self._switch_direction = None
        self._switch_command = None

    def set_config(self, config):
        super().set_config(config)


    def proceed_enocean(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", self.packet_type_text(packet.rorg))
            return
        if packet.rorg != self._enocean_rorg:
            self._logger.debug("skipped packet with rorg=%s", hex(packet.rorg))
            return

        self._update_enocean_activity()

        data = self._extract_message(packet)
        self._logger.debug("proceed_enocean - got: %s", data)

        # input: {'COM': 2, 'EDIM': 33, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 1, 'RSSI': -55}

        rssi = packet.dBm  # if hasattr(packet, "dBm") else None
        switch_state = self.extract_switch_state(data.get("SW"))
        dim_state = self.extract_dim_state(value=data.get("EDIM"), range=data.get("EDIMR"))

        if (switch_state == StateValue.ERROR or dim_state is None) and \
                self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("proceed_enocean - pickled error packet:\n%s", Tools.pickle_packet())

        message = self._create_message(switch_state, dim_state, rssi)
        self._publish(message)

    def _create_message(self, switch_state: StateValue, dim_state: Optional[int], rssi: Optional[int] = None):
        data = {
            Fud61OutAttr.TIMESTAMP.value: self._now().isoformat(),
            Fud61OutAttr.STATE.value: switch_state.value
        }
        if rssi is not None:
            data[Fud61OutAttr.RSSI.value] = rssi
        if dim_state is not None:
            data[Fud61OutAttr.DIM.value] = dim_state

        json_text = json.dumps(data)
        return json_text

    @classmethod
    def extract_switch_state(cls, value):
        if value == 1:
            return StateValue.ON
        elif value == 0:
            return StateValue.OFF
        else:
            return StateValue.ERROR

    @classmethod
    def extract_dim_state(cls, value, range):
        if value is None:
            return None
        if range == 0:
            return value
        elif range == 1:
            return int(value / 256 + 0.5)
        else:
            return None

    def set_enocean(self, enocean):
        super().set_enocean(enocean)
        self._send_switch()

    def _create_switch_packet(self, action):
        # simulate rocker switch

        if action == SwitchAction.ON:
            props = {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        elif action == SwitchAction.OFF:
            props = {'R1': 0, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        elif action == SwitchAction.RELEASE:
            props = {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}
        else:
            RuntimeError()

        # could also b e 0xffffffff
        destination = Tools.int_to_byte_list(self._enocean_id, 4)

        packet = RadioPacket.create(
            rorg=self._switch_rorg,
            rorg_func=self._switch_func,
            rorg_type=self._switch_type,
            destination=destination,
            learn=False,
            **props
        )
        return packet

    def get_teach_message(self):
        return "A rocker switch is simulated for switching! Set teach target to EC1 == direction switch!"

    def send_teach_message(self):
        self._simulate_button_press(SwitchAction.ON)

    def _simulate_button_press(self, action: SwitchAction):

        if action != SwitchAction.RELEASE:
            packet = self._create_switch_packet(action)
            self._send_enocean_packet(packet)
            time.sleep(0.05)

        packet = self._create_switch_packet(SwitchAction.RELEASE)
        self._send_enocean_packet(packet)

    def _send_switch(self):
        key = "last_action"

        # curr_action = True

        button_action = SwitchAction.ON if curr_action else SwitchAction.OFF
        self._logger.info("switch {}".format(button_action.value))
        self._simulate_button_press(button_action)
