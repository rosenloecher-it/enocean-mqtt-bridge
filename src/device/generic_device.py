import json

from src.device.base_device import BaseDevice


class GenericDevice(BaseDevice):
    """
    specialized class to forward notfications of Eltako FFG7B-rw (Eltako TF-FGB) windows/door handles

    output is a json dict with values of `HandleState`

    no information is sent to the device!
    """

    def __init__(self, name):
        super().__init__(name)

    def proceed_enocean(self, message):
        self._update_enocean_activity()

        try:
            data = self._extract_message(message.payload)
            message = json.dumps(data)
        except Exception as ex:
            message = str(ex)

        self._logger.info("proceed_enocean - send: %s", message)
        self._publish(message)
