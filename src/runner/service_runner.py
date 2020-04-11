import logging
import time
from typing import List

import paho.mqtt.client as mqtt

from src.config import ConfSectionKey
from src.device.base_device import BaseDevice
from src.device.device_exception import DeviceException
from src.mqtt_connector import MqttConnector
from src.mqtt_publisher import MqttPublisher
from src.runner.runner import Runner

_logger = logging.getLogger(__name__)


class ServiceRunner(Runner):

    def __init__(self):
        super().__init__()

        self._enocean_ids = {}  # type: dict[int, List[BaseDevice]]
        self._mqtt_last_will_channels = {}  # type: dict[str, BaseDevice]
        self._mqtt_channels_subscriptions = {}  # type: dict[str, set[BaseDevice]]

        self._mqtt_publisher = MqttPublisher()

        self._mqtt_connector = MqttConnector(self._mqtt_publisher)
        self._mqtt_connector.on_connect = self._on_mqtt_connect
        self._mqtt_connector.on_message = self._on_mqtt_message

    def run(self):
        self._init_devices()
        self._collect_mqtt_subscriptions()

        self._mqtt_connector.open(self._config)

        self._connect_enocean()

        self._loop()

    def close(self):
        super().close()

        if self._mqtt_connector is not None:
            for channel, device in self._mqtt_last_will_channels.items():
                try:
                    device.close_mqtt()
                except DeviceException as ex:
                    _logger.error(ex)

            self._enocean_ids = {}
            self._mqtt_last_will_channels = {}
            self._mqtt_channels_subscriptions = {}

            self._mqtt_connector.close()
            self._mqtt_connector = None
            _logger.debug("mqtt closed.")

    def _loop(self):
        time_step = 0.05
        time_wait_for_refresh = 0
        time_check_offline = 0

        try:
            while not self._shutdown:
                if time_wait_for_refresh >= 30:
                    time_wait_for_refresh = 0
                    self._enocean.assure_connection()

                self._enocean.handle_messages()

                if time_check_offline >= 5:
                    self._check_and_send_offline()

                time.sleep(time_step)
                time_wait_for_refresh += time_step
                time_check_offline += time_step

        except KeyboardInterrupt:
            # gets called without signal-handler
            _logger.debug("finishing...")
        finally:
            self.close()

    def _check_and_send_offline(self):
        for device in self._mqtt_last_will_channels.values():
            device.check_and_send_offline()

    def _on_enocean_receive(self, message):
        """
        :param src.enocean_interface.EnoceanMessage message:
        """
        listener = self._enocean_ids.get(message.enocean_id) or []

        if message.enocean_id is not None:
            none_listener = self._enocean_ids.get(None)
            if none_listener:
                listener.extend(none_listener)

        if listener:
            for device in listener:
                device.process_enocean_message(message)
        # else:
        #     _logger.debug("enocean receiver not found - cannot proceed message '%s'", message)

    def _on_mqtt_connect(self, rc):
        if rc == 0:
            try:
                channels = [c for c in self._mqtt_channels_subscriptions]
                self._mqtt_connector.subscribe(channels)

                for id, devices in self._enocean_ids.items():
                    for device in devices:
                        device.open_mqtt()

            except Exception as ex:
                _logger.exception(ex)

    def _on_mqtt_message(self, message):
        try:
            devices = self._mqtt_channels_subscriptions.get(message.topic)
            for device in devices:
                device.process_mqtt_message(message)
        except Exception as ex:
            _logger.exception(ex)

    def _init_devices(self):
        items = self._config[ConfSectionKey.DEVICES.value]
        for name, config in items.items():
            try:
                self._init_device(name, config)
            except DeviceException as ex:
                _logger.error(ex)

    def _init_device(self, name, config):
        device_instance = self._create_device(name, config)

        device_instance.set_mqtt_publisher(self._mqtt_publisher)

        enocean_ids = device_instance.enocean_ids
        if enocean_ids is None:
            # interprete as listen to all (LogDevice)!
            enocean_ids = [None]
        for enocean_id in enocean_ids:
            former_devices = self._enocean_ids.get(enocean_id)
            if former_devices is not None:
                former_devices.append(device_instance)
            else:
                self._enocean_ids[enocean_id] = [device_instance]

        channel = device_instance.get_mqtt_last_will_channel()
        if channel:
            # former last wills could be overwritten, no matter
            self._mqtt_last_will_channels[channel] = device_instance

    def _connect_enocean(self):
        super()._connect_enocean()

        for id, devices in self._enocean_ids.items():
            for device in devices:
                device.set_enocean(self._enocean)

    def _collect_mqtt_subscriptions(self):
        self._mqtt_channels_subscriptions = {}

        for id, devices in self._enocean_ids.items():
            for device in devices:
                channels = device.get_mqtt_channel_subscriptions()
                if channels:
                    for channel in channels:
                        if channel is None:
                            continue
                        devices = self._mqtt_channels_subscriptions.get(channel)
                        if devices is None:
                            devices = set()
                            self._mqtt_channels_subscriptions[channel] = devices
                        devices.add(device)

    def _subscribe_mqtt(self):
        subs_qos = 1  # qos for subscriptions, not used, but neccessary
        subscriptions = [(s, subs_qos) for s in self._mqtt_channels_subscriptions]
        if subscriptions:
            result, dummy = self._mqtt_connector.subscribe(subscriptions)
            if result != mqtt.MQTT_ERR_SUCCESS:
                text = "could not subscripte to mqtt #{} ({})".format(result, subscriptions)
                raise RuntimeError(text)

            _logger.info("subscripted to MQTT channels")
