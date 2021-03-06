import logging
from collections import namedtuple

from src.common.conf_device_key import ConfDeviceKey
from src.common.eep import Eep
from src.config import Config
from src.device.base_rocker_actor import BaseRockerActor, SwitchState, ActorCommand
from src.enocean_connector import EnoceanMessage
from src.tools.pickle_tools import PickleTools

_Notification = namedtuple("_Notification", ["channel", "switch_state"])


class NodonSin22Actor(BaseRockerActor):
    """Actor for Nodon SIN-2-2-01"""

    DEFAULT_EEP = Eep(
        rorg=0xd2,
        func=0x01,
        type=0x01,  # type should be 0x02, but it's not available within "enocean" lib
        direction=None,
        command=None  # 0x01
    )

    def __init__(self, name):
        super().__init__(name)

        self._time_between_rocker_commands = 0.2
        self._eep = self.DEFAULT_EEP.clone()
        self._actor_channel = None

    def set_config(self, config):
        super().set_config(config)

        self._actor_channel = Config.get_int(config, ConfDeviceKey.ACTOR_CHANNEL)
        if self._actor_channel is None:
            raise ValueError(f"No configuration for '{ConfDeviceKey.ACTOR_CHANNEL.value}'!")

    def process_enocean_message(self, message: EnoceanMessage):
        packet = self._extract_default_radio_packet(message)
        if not packet:
            return

        data = self._extract_packet_props(packet)
        self._logger.debug("proceed_enocean - got: %s", data)

        notification = self.extract_notification(data)
        if notification.channel != self._actor_channel:
            self._logger.debug("skip channel (%s, awaiting=%s)", notification.channel, self._actor_channel)
            return

        rssi = packet.dBm  # if hasattr(packet, "dBm") else None

        if notification.switch_state == SwitchState.ERROR and self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("process_enocean_message - pickled error packet:\n%s", PickleTools.pickle_packet(packet))

        message = self._create_json_message(notification.switch_state, None, rssi)
        self._publish_mqtt(message)

    @classmethod
    def extract_notification(cls, data):
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 1, 'LC': 1, 'OV': 0}
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 0, 'LC': 1, 'OV': 100}
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 1, 'LC': 1, 'OV': 100}
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 0, 'LC': 1, 'OV': 0}
        value = int(data.get("OV"))

        if value == 0:
            switch_state = SwitchState.OFF
        elif 0 < value <= 100:
            switch_state = SwitchState.ON
        else:
            switch_state = SwitchState.ERROR

        return _Notification(channel=int(data.get("IO")), switch_state=switch_state)

    def get_teach_print_message(self):
        return "Nodon SIN-2-2-01: 1 channel per configured device (no parameters)!"

    def send_teach_telegram(self, cli_arg):
        command = ActorCommand.ON

        if cli_arg:
            try:
                command = self.extract_actor_command(cli_arg)
            except ValueError:
                raise ValueError("could not interprete teach argument ({})!".format(cli_arg))

        self._execute_actor_command(command, learn=False)
