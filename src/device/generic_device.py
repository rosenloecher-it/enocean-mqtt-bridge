import json

from enocean.protocol.constants import PACKET
from enocean.protocol.packet import Packet

from src.device.base_device import BaseDevice
from src.enocean_connector import EnoceanMessage


class GenericDevice(BaseDevice):
    """
    specialized class to forward notfications of Eltako FFG7B-rw (Eltako TF-FGB) windows/door handles

    output is a json dict with values of `HandleState`

    no information is sent to the device!
    """

    def __init__(self, name):
        super().__init__(name)

    def process_enocean_message(self, message: EnoceanMessage):

        packet = message.payload  # type: Packet
        if packet.packet_type != PACKET.RADIO:
            return

        self._update_enocean_activity()

        try:
            data = self._extract_message(message.payload)
            message = json.dumps(data)
        except Exception as ex:
            message = str(ex)

        self._publish_mqtt(message)
