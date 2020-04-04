from enum import Enum

import time
from enocean.protocol.constants import PACKET, RETURN_CODE
from enocean.protocol.packet import Packet, RadioPacket

from src.config import Config
from src.device.base_device import BaseDevice
from src.enocean_connector import EnoceanMessage
from src.storage import Storage, StorageException
from src.tools import Tools


class ButtonAction(Enum):
    ON = "on"  # press
    OFF = "off"  # press
    RELEASE = "release"


class ConfDeviceExKey(Enum):
    STORAGE_FILE = "storage_file"


PACKET_STATUS_ON_33 = """
gANjZW5vY2Vhbi5wcm90b2NvbC5wYWNrZXQKUmFkaW9QYWNrZXQKcQApgXEBfXECKFgLAAAAcGFj
a2V0X3R5cGVxA0sBWAQAAAByb3JncQRLpVgJAAAAcm9yZ19mdW5jcQVOWAkAAAByb3JnX3R5cGVx
Bk5YEQAAAHJvcmdfbWFudWZhY3R1cmVycQdOWAgAAAByZWNlaXZlZHEIY2RhdGV0aW1lCmRhdGV0
aW1lCnEJQwoH5AMdECwNB6j9cQqFcQtScQxYBAAAAGRhdGFxDV1xDihLpUsCSyFLAEsJSwVLGksu
S3xLAGVYCAAAAG9wdGlvbmFscQ9dcRAoSwBL/0v/S/9L/0s3SwBlWAYAAABzdGF0dXNxEUsAWAYA
AABwYXJzZWRxEmNjb2xsZWN0aW9ucwpPcmRlcmVkRGljdApxEylScRRYDgAAAHJlcGVhdGVyX2Nv
dW50cRVLAFgIAAAAX3Byb2ZpbGVxFk5YCwAAAGRlc3RpbmF0aW9ucRddcRgoS/9L/0v/S/9lWAMA
AABkQm1xGUrJ////WAYAAABzZW5kZXJxGl1xGyhLBUsaSy5LfGVYBQAAAGxlYXJucRyJdWIu
"""


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

        # simulate rocjker switch
        self._switch_rorg = 0xf6
        self._switch_func = 0x02
        self._switch_type = 0x02
        self._switch_direction = None
        self._switch_command = None

        self._storage = Storage()

    def set_config(self, config):
        super().set_config(config)

        storage_file = Config.post_process_str(self._config, ConfDeviceExKey.STORAGE_FILE, None)
        self._storage.set_file(storage_file)

        try:
            self._storage.load()
        except StorageException as ex:
            self._logger.exception(ex)

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

        # check packet type
        if packet.packet_type == PACKET.RADIO:
            # self._process_packet(packet)
            self._logger.debug("TODO process_packet")
        elif packet.packet_type == PACKET.RESPONSE:
            response_code = RETURN_CODE(packet.data[0])
            self._logger.warning("TODO got response packet: {}".format(response_code.name))
        else:
            self._logger.debug("TODO got non-RF packet: {}".format(packet))

        # try:
        #     rssi = data.get(PropName.RSSI.value)
        #     value = self.extract_handle_state(data.get("WIN"))
        # except DeviceException as ex:
        #     self._logger.exception(ex)
        #     value = HandleValue.ERROR
        #
        # if value == HandleValue.ERROR and self._logger.isEnabledFor(logging.DEBUG):
        #     # write ascii representation to reproduce in tests
        #     self._logger.debug("proceed_enocean - pickled error packet:\n%s", Tool.pickle(packet))
        #
        # if self._write_since:
        #     since = self._determine_and_store_since(value)
        # else:
        #     since = None
        #
        # message = self._create_message(value, since, rssi)
        # self._publish(message)

    def set_enocean(self, enocean):
        super().set_enocean(enocean)
        self._send_switch()

    def _create_packet(self, action):
        # simulate rocker switch

        if action == ButtonAction.ON:
            props = {'R1': 1, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        elif action == ButtonAction.OFF:
            props = {'R1': 0, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        elif action == ButtonAction.RELEASE:
            props = {'R1': 0, 'EB': 0, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 0}
        else:
            RuntimeError()

        # destination = Tools.int_to_byte_list(0xffffffff, 4)
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
        self._simulate_button_press(ButtonAction.ON)

    def _simulate_button_press(self, action: ButtonAction):

        if action != ButtonAction.RELEASE:
            packet = self._create_packet(action)
            self._send_enocean_packet(packet)
            time.sleep(0.05)

        packet = self._create_packet(ButtonAction.RELEASE)
        self._send_enocean_packet(packet)

    def _send_switch(self):
        key = "last_action"

        last_action = self._storage.get(key, False)
        curr_action = not last_action
        self._storage.set(key, curr_action)
        try:
            self._storage.save()
        except StorageException as ex:
            self._logger.exception(ex)

        # curr_action = True

        button_action = ButtonAction.ON if curr_action else ButtonAction.OFF
        self._logger.info("switch {}".format(button_action.value))
        self._simulate_button_press(button_action)
