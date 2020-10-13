import logging

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.conf_device_key import ConfDeviceKey
from src.device.device_exception import DeviceException
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class LogDevice(BaseDevice):

    def __init__(self, name):
        super().__init__(name)

        self._enocean_ids = None
        self._enocean_ids_skip = None
        self._dump_packet = False

    @property
    def enocean_targets(self):
        return self._enocean_ids

    def _check_mqtt_channel(self):
        pass

    def set_config(self, config):
        # don't call base function

        def add_id_not_none(target, input):
            if input is None:
                return
            elif type(input) == int:
                target.add(id)
            else:
                for i in input:
                    target.add(i)

        self._enocean_ids = set()
        self._enocean_ids_skip = set()

        if self._enocean_target is None:
            self._enocean_ids.add(None)  # listen to all!
        else:
            add_id_not_none(self._enocean_ids, self._enocean_target)
            add_id_not_none(self._enocean_ids, config.get(ConfDeviceKey.ENOCEAN_IDS.value))

        add_id_not_none(self._enocean_ids_skip, config.get(ConfDeviceKey.ENOCEAN_IDS_SKIP.value))

        self._dump_packet = Config.get_bool(config, ConfDeviceKey.DUMP_PACKETS, False)

    def process_enocean_message(self, message):
        packet = message.payload
        if packet.sender_int in self._enocean_ids_skip:
            return

        packet_type = PickleTools.extract_packet_type_text(packet.packet_type)

        self._logger.info("proceed_enocean - packet(%s): %s", packet_type, packet)

        if self._dump_packet and self._logger.isEnabledFor(logging.INFO):
            self._logger.info("proceed_enocean - dump:\n%s", EnoceanTools.pickle_packet(packet))

        # self._try_to_extract(packet, 0xf6, 0x02, 0x02)

        if None not in [self._eep.func, self._eep.rorg, self._eep.type]:
            try:
                data = self._extract_packet(packet)
                self._logger.info("proceed_enocean - extracted: %s", data)
            except DeviceException as ex:
                self._logger.exception("proceed_enocean - could not extract:\n%s", ex)

    def set_last_will(self):
        pass
