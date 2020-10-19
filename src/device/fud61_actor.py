import logging

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet

from src.device.rocker_actor import RockerActor, StateValue, ActorCommand
from src.eep import Eep
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class Fud61Actor(RockerActor):
    """
    Specialized for: Eltako FUD61NP(N)-230V (dimmer)

    Unfortunately I was not able to set diectly the dim state. Instead I use rockr switch telegrams to switct ON/OFF.
    A real dim operation is impractical this way, so only ON/OFF can be switched. At last the dim state get notfied
    via confirmation telegrams.

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

    Don't forget toteach such devices.

    See also:
    - https://www.eltako.com/fileadmin/downloads/de/Gesamtkatalog/Eltako_Gesamtkatalog_KapT_low_res.pdf
    - https://github.com/kipe/enocean/blob/master/SUPPORTED_PROFILES.md
    """
    DEFAULT_EEP = Eep(
        rorg=0xa5,
        func=0x38,
        type=0x08,
        direction=None,
        command=0x02
    )

    def __init__(self, name):
        super().__init__(name)

        self._eep = self.DEFAULT_EEP

    def process_enocean_message(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return
        if packet.rorg != self._eep.rorg:
            self._logger.debug("skipped packet with rorg=%s", hex(packet.rorg))
            return

        data = self._extract_packet_props(packet)
        self._logger.debug("proceed_enocean - got: %s", data)

        # input: {'COM': 2, 'EDIM': 33, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 1, 'RSSI': -55}

        rssi = packet.dBm  # if hasattr(packet, "dBm") else None
        switch_state = self.extract_switch_state(data.get("SW"))
        dim_state = self.extract_dim_state(value=data.get("EDIM"), range=data.get("EDIMR"))

        if (switch_state == StateValue.ERROR or dim_state is None) and \
                self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("proceed_enocean - pickled error packet:\n%s", PickleTools.pickle_packet())

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
        self._execute_actor_command(ActorCommand.ON)
