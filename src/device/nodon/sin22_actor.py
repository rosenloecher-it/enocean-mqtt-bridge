import logging
from collections import namedtuple

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import RadioPacket

from src.common.eep import Eep
from src.device.base.rocker_actor import RockerActor, SwitchStatus
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


CONFKEY_ACTOR_CHANNEL = "actor_channel"


SIN22ACTOR_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_ACTOR_CHANNEL: {"type": "integer", "enum": [0, 1]},

    },
    "required": [CONFKEY_ACTOR_CHANNEL],
}


_Notification = namedtuple("_Notification", ["channel", "switch_state"])


class Sin22Actor(RockerActor):
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

    def _set_config(self, config, skip_require_fields: [str]):
        super()._set_config(config, skip_require_fields)

        schema = self.filter_required_fields(SIN22ACTOR_JSONSCHEMA, skip_require_fields)
        self.validate_config(config, schema)

        self._actor_channel = config[CONFKEY_ACTOR_CHANNEL]

    def process_enocean_message(self, message: EnoceanMessage):
        packet: RadioPacket = message.payload
        if packet.packet_type != PACKET.RADIO:
            self._logger.debug("skipped packet with packet_type=%s", EnoceanTools.packet_type_to_string(packet.rorg))
            return
        if packet.rorg != self._eep.rorg:
            self._logger.debug("skipped packet with rorg=%s", hex(packet.rorg))
            return

        data = EnoceanTools.extract_packet_props(packet, self._eep)
        self._logger.debug("proceed_enocean - got: %s", data)

        notification = self.extract_notification(data)
        if notification.channel != self._actor_channel:
            self._logger.debug("skip channel (%s, awaiting=%s)", notification.channel, self._actor_channel)
            return

        if notification.switch_state == SwitchStatus.ERROR and self._logger.isEnabledFor(logging.DEBUG):
            # write ascii representation to reproduce in tests
            self._logger.debug("process_enocean_message - pickled error packet:\n%s", PickleTools.pickle_packet(packet))

        message = self._create_json_message(notification.switch_state, None)
        self._publish_mqtt(message)

    @classmethod
    def extract_notification(cls, data):
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 1, 'LC': 1, 'OV': 0}
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 0, 'LC': 1, 'OV': 100}
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 1, 'LC': 1, 'OV': 100}
        # {'PF': 0, 'PFD': 0, 'CMD': 4, 'OC': 0, 'EL': 3, 'IO': 0, 'LC': 1, 'OV': 0}
        value = int(data.get("OV"))

        if value == 0:
            switch_state = SwitchStatus.OFF
        elif 0 < value <= 100:
            switch_state = SwitchStatus.ON
        else:
            switch_state = SwitchStatus.ERROR

        return _Notification(channel=int(data.get("IO")), switch_state=switch_state)
