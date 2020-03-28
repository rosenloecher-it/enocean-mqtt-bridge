import logging

from src.device.base_device import BaseDevice
from src.device.device_exception import DeviceException
from src.tools import Tool


class LogDevice(BaseDevice):

    def set_config(self, config):
        super().set_config(config)

    def _check_mqtt_channel(self):
        pass

    def proceed_enocean(self, message):
        self._update_enocean_activity()

        packet = message.payload
        self._logger.debug("proceed_enocean - packet:\n  %s", packet)

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug("proceed_enocean - pickled:\n%s", Tool.pickle(packet))

        try:
            data = self._extract_message(packet, store_extra_data=True)
            self._logger.info("proceed_enocean - extracted:\n  %s", data)
        except DeviceException as ex:
            self._logger.exception("proceed_enocean - could not extract:\n%s", ex)

    def _publish(self, message: str):
        pass

    def set_last_will(self):
        pass
