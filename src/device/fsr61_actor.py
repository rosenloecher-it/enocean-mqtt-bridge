import logging

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet

from src.device.rocker_actor import RockerActor, StateValue, ActorCommand
from src.enocean_connector import EnoceanMessage
from src.tools import Tools


class Fsr61Actor(RockerActor):
    """
    Eltako FSR61-230V

    The confirmation telegrams my device is sending does not match the specification.
    Expected EEP: A5-12-01

    But I got a rocker switch telegram (F6-02-02) !? So far it works.

    See: https://www.eltako.com/fileadmin/downloads/de/Gesamtkatalog/Eltako_Gesamtkatalog_KapT_low_res.pdf
    """

    DEFAULT_ENOCEAN_RORG = 0xf6
    DEFAULT_ENOCEAN_FUNC = 0x02  # 0x12
    DEFAULT_ENOCEAN_TYPE = 0x02  # 0x01

    DEFAULT_ENOCEAN_DIRECTION = None
    DEFAULT_ENOCEAN_COMMAND = None  # 0x01

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

        rssi = packet.dBm  # if hasattr(packet, "dBm") else None
        switch_state = self.extract_switch_state(data)

        if switch_state == StateValue.ERROR and self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("proceed_enocean - pickled error packet:\n%s", Tools.pickle_packet(packet))

        message = self._create_message(switch_state, None, rssi)
        self._publish_mqtt(message)

    @classmethod
    def extract_switch_state(cls, data):
        # ON  {'R1': 3, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}
        # OFF {'R1': 2, 'EB': 1, 'R2': 0, 'SA': 0, 'T21': 1, 'NU': 1}

        value = data.get("R1")

        if value == 3:
            return StateValue.ON
        elif value == 2:
            return StateValue.OFF
        else:
            return StateValue.ERROR

    def get_teach_print_message(self):
        return \
            "FSR61: A rocker switch is simulated for switching!\n" \
            "- Set teach target to '40' == direction switch!\n" \
            "- Activate confirmations telegrams (extra step)!"

    def send_teach_telegram(self, cli_arg):
        command = ActorCommand.ON
        if cli_arg:
            try:
                command = self.extract_actor_command(cli_arg)
            except ValueError:
                raise ValueError("could not interprete teach argument ({})!".format(cli_arg))

        self._execute_actor_command(command, learn=True)
