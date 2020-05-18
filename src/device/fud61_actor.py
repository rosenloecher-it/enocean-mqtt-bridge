import logging
import time

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet

from src.config import ConfMainKey
from src.device.eltako_on_off_actor import EltakoOnOffActor, SwitchAction, StateValue
from src.enocean_connector import EnoceanMessage
from src.tools import Tools


class Fud61Actor(EltakoOnOffActor):
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

    DEFAULT_ENOCEAN_RORG = 0xa5
    DEFAULT_ENOCEAN_FUNC = 0x38
    DEFAULT_ENOCEAN_TYPE = 0x08

    DEFAULT_ENOCEAN_DIRECTION = None
    DEFAULT_ENOCEAN_COMMAND = 0x02

    def __init__(self, name):
        super().__init__(name)

        # default config values
        self._enocean_rorg = self.DEFAULT_ENOCEAN_RORG
        self._enocean_func = self.DEFAULT_ENOCEAN_FUNC
        self._enocean_type = self.DEFAULT_ENOCEAN_TYPE
        self._enocean_direction = self.DEFAULT_ENOCEAN_DIRECTION
        self._enocean_command = self.DEFAULT_ENOCEAN_COMMAND

    def process_enocean_message(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", Tools.packet_type_text(packet.rorg))
            return
        if packet.rorg != self._enocean_rorg:
            self._logger.debug("skipped packet with rorg=%s", hex(packet.rorg))
            return

        data = self._extract_packet(packet)
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
        self._publish_mqtt(message)

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

    def get_teach_print_message(self):
        return \
            "FUD61: A rocker switch is simulated for switching!\n" \
            "- Set teach target to EC1 == direction switch!\n" \
            "- Activate confirmations telegrams (extra step)!"

    def send_teach_telegram(self, cli_arg):
        action = SwitchAction.ON
        self._simulate_button_press(action)

    def _simulate_button_press(self, action: SwitchAction):

        if action != SwitchAction.RELEASE:
            packet = self._create_switch_packet(action)
            self._send_enocean_packet(packet)
            time.sleep(0.05)

        packet = self._create_switch_packet(SwitchAction.RELEASE)
        self._send_enocean_packet(packet)

    def process_mqtt_message(self, message):
        """

        :param src.enocean_interface.EnoceanMessage message:
        """
        self._logger.debug('process_mqtt_message: "%s"', message.payload)

        payload = message.payload
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        try:
            switch_action = self.extract_switch_action(payload)
            self._logger.debug("switch to {}".format(switch_action.value))
            self._simulate_button_press(switch_action)
        except ValueError:
            self._logger.error("cannot switch, message: {}".format(payload))
