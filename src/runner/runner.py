import abc
import logging
import signal
import threading
import time
from enum import IntEnum
from typing import Dict, List, Set, Optional

from enocean import utils as enocean_utils

from src.common.config_exception import ConfigException
from src.config import CONFKEY_DEVICES, CONFKEY_ENOCEAN_PORT, CONFKEY_MAIN
from src.device.base.cyclic_device import CheckCyclicTask
from src.device.base.device import Device
from src.common.device_exception import DeviceException
from src.enocean_connector import EnoceanConnector
from src.enocean_packet_factory import EnoceanPacketFactory
from src.mqtt_connector import MqttConnector
from src.mqtt_publisher import MqttPublisher
from src.runner.device_factory import DeviceFactory

_logger = logging.getLogger(__name__)


class _MqttState(IntEnum):
    UNINITIALED = 0
    INITIALISING = 1
    CONNECTED = 2
    DISCONNECTED = 3


class Runner(abc.ABC):

    def __init__(self):
        self._config = None
        self._enocean_connector = None
        self._shutdown = False

        self._enocean_ids: Dict[int, List[Device]] = {}
        self._mqtt_last_will_channels: Dict[str, Device] = {}
        self._mqtt_channels_subscriptions: Dict[str, Set[Device]] = {}

        self._devices_check_cyclic = set()

        self._mqtt_publisher = MqttPublisher()
        self._mqtt_connector: Optional[MqttConnector] = None

        self._mqtt_state = _MqttState.UNINITIALED
        self._mqtt_lock = threading.Lock()

        signal.signal(signal.SIGINT, self._shutdown_gracefully)
        signal.signal(signal.SIGTERM, self._shutdown_gracefully)

    def _shutdown_gracefully(self, sig, _frame):
        _logger.info("shutdown signaled (%s)", sig)
        self._shutdown = True

    def __del__(self):
        self.close()

    def open(self, config):
        self._config = config
        # if _logger.isEnabledFor(logging.DEBUG):
        #     pretty = json.dumps(self._config, indent=4, sort_keys=True)
        #     _logger.debug("config: %s", pretty)

        self._init_devices()

        self._mqtt_connector = MqttConnector(self._mqtt_publisher)
        self._mqtt_connector.on_connect = self._on_mqtt_connect
        self._mqtt_connector.on_disconnect = self._on_mqtt_disconnect

        self._collect_mqtt_subscriptions()
        self._mqtt_connector.open(self._config[CONFKEY_MAIN])

        self._connect_enocean()

    def close(self):
        self._mqtt_channels_subscriptions = {}  # no commands will be executed anymore

        if self._enocean_connector is not None:  # and self._enocean.is_alive():
            self._enocean_connector.close()
            self._enocean_connector = None

        if self._mqtt_connector is not None:
            for channel, device in self._mqtt_last_will_channels.items():
                try:
                    device.close_mqtt()
                except DeviceException as ex:
                    _logger.error(ex)

            self._enocean_ids = {}
            self._mqtt_last_will_channels = {}
            self._mqtt_channels_subscriptions = {}
            self._devices_check_cyclic = set()

            self._mqtt_connector.close()
            self._mqtt_connector = None
            _logger.debug("mqtt closed.")

    def run(self):
        """endless loop"""
        time_step = 0.05
        time_wait_for_refresh = 0
        time_check_offline = 0

        self._wait_for_base_id()
        self._wait_for_mqtt_connection()

        try:
            while not self._shutdown:
                busy = False

                if time_wait_for_refresh >= 30:
                    time_wait_for_refresh = 0
                    self._enocean_connector.assure_connection()

                if self._process_enocean_messages():
                    busy = True
                if self._process_mqtt_messages():
                    busy = True

                if time_check_offline >= 5:
                    time_check_offline = 0
                    self._check_cyclic_tasks()

                if not busy:
                    self._mqtt_connector.ensure_connection()
                    time.sleep(time_step)
                    time_wait_for_refresh += time_step
                    time_check_offline += time_step

        except KeyboardInterrupt:
            # gets called without signal-handler
            _logger.debug("finishing...")
        finally:
            self.close()

    def _connect_enocean(self):
        port = self._config[CONFKEY_MAIN][CONFKEY_ENOCEAN_PORT]  # validated
        self._enocean_connector = EnoceanConnector(port)
        self._enocean_connector.open()

        for _, devices in self._enocean_ids.items():
            for device in devices:
                device.set_enocean_connector(self._enocean_connector)

    def _wait_for_base_id(self):
        """wait until the base id is ready"""
        time_step = 0.05
        time_counter = 0

        while not self._shutdown:
            # wait for getting the adapter id
            time.sleep(time_step)
            time_counter += time_step
            if time_counter > 30:
                raise RuntimeError("Couldn't get my own Enocean ID!?")
            base_id = self._enocean_connector.base_id
            if base_id:
                # got a base id
                EnoceanPacketFactory.set_sender_id(base_id)
                if type(base_id) == list:
                    base_id = enocean_utils.combine_hex(base_id)
                _logger.info("base_id=%s", hex(base_id))
                break

    def _wait_for_mqtt_connection(self):
        """wait for getting mqtt connect callback called"""
        time_step = 0.05
        time_counter = 0

        while not self._shutdown:
            time.sleep(time_step)
            time_counter += time_step
            if time_counter > 15:
                raise RuntimeError("Couldn't connect to MQTT, callback was not called!?")

            with self._mqtt_lock:
                if self._mqtt_state == _MqttState.INITIALISING:
                    channels = [c for c in self._mqtt_channels_subscriptions]
                    self._mqtt_connector.subscribe(channels)

                    self._mqtt_publisher.open(self._mqtt_connector)
                    self._mqtt_state = _MqttState.CONNECTED

                    for _, devices in self._enocean_ids.items():
                        for device in devices:
                            device.open_mqtt()

                    break

    def _process_mqtt_messages(self) -> bool:
        busy = False
        messages = self._mqtt_connector.get_queued_messages()
        for message in messages:
            try:
                devices = self._mqtt_channels_subscriptions.get(message.topic)
                for device in devices:
                    device.process_mqtt_message(message)
                    busy = True
            except Exception as ex:
                _logger.exception(ex)

        return busy

    def _process_enocean_messages(self) -> bool:
        busy = False

        messages = self._enocean_connector.get_messages()
        for message in messages:
            try:
                listener = self._enocean_ids.get(message.enocean_id) or []
                if message.enocean_id is not None:
                    none_listener = self._enocean_ids.get(None)
                    if none_listener:
                        listener.extend(none_listener)
                if listener:
                    for device in listener:
                        device.process_enocean_message(message)
            except Exception as ex:
                _logger.exception(ex)
            busy = True

        return busy

    def _check_cyclic_tasks(self):
        for device in self._devices_check_cyclic:
            device.check_cyclic_tasks()

    def _on_mqtt_connect(self, rc):
        """Notify MQTT connection state; callback from MQTT network thread"""
        with self._mqtt_lock:
            if rc == 0:
                if self._mqtt_state == _MqttState.UNINITIALED:
                    self._mqtt_state = _MqttState.INITIALISING
            else:
                self._mqtt_state = _MqttState.DISCONNECTED

    def _on_mqtt_disconnect(self, _rc):
        with self._mqtt_lock:
            self._mqtt_state = _MqttState.DISCONNECTED

    def _init_devices(self):
        found_configuration_errors = False

        items = self._config[CONFKEY_DEVICES]
        for name, config in items.items():
            try:
                self._init_device(name, config)
            except DeviceException as ex:
                _logger.error(ex)
                found_configuration_errors = True

        if found_configuration_errors:
            raise ConfigException("Found configuration errors!?")

    def _init_device(self, name, config):
        device_instance = DeviceFactory.create_device(name, config)

        enocean_ids = device_instance.enocean_targets
        if enocean_ids is None:
            # interprete as listen to all (LogDevice)!
            enocean_ids = [None]
        for enocean_id in enocean_ids:
            former_devices = self._enocean_ids.get(enocean_id)
            if former_devices is not None:
                former_devices.append(device_instance)
            else:
                self._enocean_ids[enocean_id] = [device_instance]

        if isinstance(device_instance, CheckCyclicTask):
            self._devices_check_cyclic.add(device_instance)

        device_instance.set_mqtt_publisher(self._mqtt_publisher)
        channel = device_instance.get_mqtt_last_will_channel()
        if channel:
            # former last wills could be overwritten, no matter
            self._mqtt_last_will_channels[channel] = device_instance

    def _collect_mqtt_subscriptions(self):
        self._mqtt_channels_subscriptions = {}

        for _, devices in self._enocean_ids.items():
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
