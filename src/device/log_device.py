import logging

from src.config import Config
from src.device.base_device import BaseDevice
from src.device.conf_device_key import ConfDeviceKey
from src.device.device_exception import DeviceException
from src.tools import Tools


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
            add_id_not_none(self._enocean_ids, self._config.get(ConfDeviceKey.ENOCEAN_IDS.value))

        add_id_not_none(self._enocean_ids_skip, self._config.get(ConfDeviceKey.ENOCEAN_IDS_SKIP.value))

        self._dump_packet = Config.post_process_bool(self._config, ConfDeviceKey.DUMP_PACKETS, False)

    def process_enocean_message(self, message):
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
                data = self._extract_message(packet)
                self._logger.info("proceed_enocean - extracted: %s", data)
            except DeviceException as ex:
                self._logger.exception("proceed_enocean - could not extract:\n%s", ex)

    def _check_enocean_settings(self):
        pass

    def _check_mqtt_settings(self):
        pass

    def _publish_mqtt(self, message: str):
        pass

    def set_last_will(self):
        pass
