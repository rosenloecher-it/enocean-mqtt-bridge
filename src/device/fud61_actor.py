import logging

from src.device.rocker_actor import RockerActor, StateValue, ActorCommand
from src.enocean_connector import EnoceanMessage
from src.tools.fud61_tools import Fud61Tools
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

    def __init__(self, name):
        super().__init__(name)

        self._eep = Fud61Tools.DEFAULT_EEP.clone()

    def process_enocean_message(self, message: EnoceanMessage):
        packet = self._extract_default_radio_packet(message)
        if not packet:
            return

        data = Fud61Tools.extract_props(packet)
        # input: {'COM': 2, 'EDIM': 33, 'RMP': 0, 'EDIMR': 0, 'STR': 0, 'SW': 1, 'RSSI': -55}
        self._logger.debug("proceed_enocean - got: %s", data)

        message = Fud61Tools.extract_message(data)

        if (message.switch_state == StateValue.ERROR or message.dim_state is None) and \
                self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("proceed_enocean - pickled error packet:\n%s", PickleTools.pickle_packet())

        message = self._create_json_message(message.switch_state, message.dim_state, message.rssi)
        self._publish_mqtt(message)

    def get_teach_print_message(self):
        return \
            "FUD61: A rocker switch is simulated for switching!\n" \
            "- Set teach target to EC1 == direction switch!\n" \
            "- Activate confirmations telegrams (extra step)!"

    def send_teach_telegram(self, cli_arg):
        self._execute_actor_command(ActorCommand.ON)
