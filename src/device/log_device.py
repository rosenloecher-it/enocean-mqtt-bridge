import logging
from enum import Enum

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.device_exception import DeviceException
from src.tools import Tools


class ConfDeviceExKey(Enum):
    DUMP_PACKETS = "dump_packets"
    ENOCEAN_IDS = "enocean_ids"
    ENOCEAN_IDS_SKIP = "enocean_ids_skip"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


class LogDevice(BaseDevice):

    def __init__(self, name):
        super().__init__(name)

        self._enocean_ids = None
        self._enocean_ids_skip = None
        self._dump_packet = False

    @property
    def enocean_ids(self):
        return self._enocean_ids

    def _check_mqtt_channel(self):
        pass

    def set_config(self, config):
        super().set_config(config)

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

        if self._enocean_id is None:
            self._enocean_ids.add(None)  # listen to all!
        else:
            add_id_not_none(self._enocean_ids, self._enocean_id)
            add_id_not_none(self._enocean_ids, self._config.get(ConfDeviceExKey.ENOCEAN_IDS.value))

        add_id_not_none(self._enocean_ids_skip, self._config.get(ConfDeviceExKey.ENOCEAN_IDS_SKIP.value))

        self._dump_packet = Config.post_process_bool(self._config, ConfDeviceExKey.DUMP_PACKETS, False)

    def proceed_enocean(self, message):
        packet = message.payload
        if packet.sender_int in self._enocean_ids_skip:
            return

        self._update_enocean_activity()

        packet_type = self.packet_type_text(packet.packet_type)

        self._logger.info("proceed_enocean - packet(%s): %s", packet_type, packet)

        if self._dump_packet and self._logger.isEnabledFor(logging.INFO):
            self._logger.info("proceed_enocean - dump:\n%s", Tools.pickle_packet(packet))

        if None not in [self._enocean_func, self._enocean_rorg, self._enocean_type]:
            try:
                data = self._extract_message(packet, store_extra_data=True)
                self._logger.info("proceed_enocean - extracted: %s", data)
            except DeviceException as ex:
                self._logger.exception("proceed_enocean - could not extract:\n%s", ex)

    def _check_enocean_settings(self):
        pass

    def _check_mqtt_settings(self):
        pass

    def _publish(self, message: str):
        pass

    def set_last_will(self):
        pass
