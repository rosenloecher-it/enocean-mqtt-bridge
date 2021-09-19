import logging

from enocean import utils as enocean_utils

from src.common.conf_device_key import ConfDeviceKey
from src.config import Config
from src.device.base.base_enocean import BaseEnocean
from src.enocean_connector import EnoceanMessage
from src.tools.enocean_tools import EnoceanTools
from src.tools.pickle_tools import PickleTools


class LogEnocean(BaseEnocean):

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

        def add_id_not_none(target, id_input):
            if id_input is None:
                return
            elif type(id_input) == int:
                target.add(id)
            else:
                for i in id_input:
                    target.add(i)

        self._enocean_ids = set()
        self._enocean_ids_skip = set()

        if self._enocean_target is not None:
            add_id_not_none(self._enocean_ids, self._enocean_target)
        else:
            enocean_ids = config.get(ConfDeviceKey.ENOCEAN_IDS.value)
            if not enocean_ids:
                self._enocean_ids.add(None)  # listen to all!
            else:
                add_id_not_none(self._enocean_ids, enocean_ids)
            add_id_not_none(self._enocean_ids_skip, config.get(ConfDeviceKey.ENOCEAN_IDS_SKIP.value))

        self._dump_packet = Config.get_bool(config, ConfDeviceKey.DUMP_PACKETS, False)

    def process_enocean_message(self, message: EnoceanMessage):
        packet = message.payload
        if packet.sender_int in self._enocean_ids_skip:
            return

        packet_type = EnoceanTools.packet_type_to_string(packet.packet_type)

        if self._dump_packet and self._logger.isEnabledFor(logging.INFO):
            self._logger.info(
                "proceed_enocean - packet: %s; sender: %s; dest: %s; RORG: %s; dump:\n%s",
                packet_type,
                packet.sender_hex,
                packet.destination_hex,
                enocean_utils.to_hex_string(packet.rorg),
                PickleTools.pickle_packet(packet)
            )
            packet.parse()
            if packet.contains_eep:
                self._logger.debug(
                    'learn received, EEP detected, RORG: 0x%02X, FUNC: 0x%02X, TYPE: 0x%02X, Manufacturer: 0x%02X' %
                    (packet.rorg, packet.rorg_func, packet.rorg_type, packet.rorg_manufacturer))  # noqa: E501

        else:
            self._logger.info(
                "proceed_enocean - packet: %s; sender: %s; dest: %s; RORG: %s",
                packet_type,
                packet.destination_hex,
                enocean_utils.to_hex_string(packet.rorg),
                packet.sender_hex
            )

    def set_last_will(self):
        pass
