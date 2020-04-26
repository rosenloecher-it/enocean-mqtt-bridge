import logging
import time

from enocean.protocol.packet import UTETeachInPacket

from src.config import ConfSectionKey, ConfMainKey
from src.runner.runner import Runner

_logger = logging.getLogger(__name__)


class TeachRunner(Runner):

    def __init__(self):
        super().__init__()

        self._device = None

    def run(self):
        self._connect_enocean()
        self._init_device()
        self._loop()

    def _init_device(self):
        name = self._config[ConfMainKey.TEACH.value]
        items = self._config[ConfSectionKey.DEVICES.value]
        device_config = items[name]

        self._device = self._create_device(name, device_config)

        self._device.set_enocean_connector(self._enocean_connector)

    def _loop(self):
        time_step = 0.05

        # print('Press and hold the teach-in button on the plug now, '
        #       'till it starts turning itself off and on (about 10 seconds or so...)')

        print("\n")
        extra_info = self._device.get_teach_print_message()
        if extra_info:
            print(extra_info)
            print("\n")

        input("\nActivate teach-in mode on your device, then press (quickly) enter.\n")

        teach_arg = self._config.get(ConfMainKey.TEACH_XTRA.value)
        self._device.send_teach_telegram(teach_arg)  # supposed to raise ex if not supported

        while not self._shutdown:
            if not self._enocean_connector.is_alive():
                raise RuntimeError("enocean is not alive!")

            self._enocean_connector.handle_messages()

            time.sleep(time_step)

    def _on_enocean_receive(self, message):
        packet = message.payload
        print("received: %s", packet)

        if isinstance(packet, UTETeachInPacket):
            print('new device learned! The ID is %s.' % (packet.sender_hex))
