import logging
import os
from argparse import ArgumentParser
from enum import Enum

import yaml

from src.common.conf_main_key import ConfMainKey


DEFAULT_CONFFILE = "/etc/enocean_mqtt_bridge.conf"


class ConfSectionKey(Enum):
    MAIN = "main"
    DEVICES = "devices"

    def __str__(self):
        return self.__repr__()

    def __repr__(self) -> str:
        return '{}'.format(self.name)


# noinspection PyCompatibility
class Config:

    CLI_KEYS_ONLY = [ConfMainKey.CONF_FILE, ConfMainKey.LOG_PRINT, ConfMainKey.SYSTEMD]

    def __init__(self, config):
        self._config = config
        self._devices = {}  # type: dict[str, dict]
        self._config[ConfSectionKey.DEVICES.value] = self._devices

    @classmethod
    def load(cls, config):
        instance = Config(config)
        instance._parse_cli()
        instance._load_conf_file()

    def _load_conf_file(self):
        conf_file = self._config[ConfMainKey.CONF_FILE.value]
        if not os.path.isfile(conf_file):
            raise FileNotFoundError('config file ({}) does not exist!'.format(conf_file))
        with open(conf_file, 'r') as stream:
            data = yaml.unsafe_load(stream)

        # main section
        def update_main(current_section, item_enum):
            item_name = item_enum.value
            value_cli = self._config.get(item_name)
            if value_cli is None:
                value_file = current_section.get(item_name)
                self._config[item_name] = value_file

        key = ConfSectionKey.MAIN.value
        section = data.get(key)
        if not section:
            raise RuntimeError("No configuration section '{}' found!".format(key))
        if not isinstance(section, dict):
            raise RuntimeError("configuration section '{}' expected to be a dictionary!".format(key))
        for e in ConfMainKey:
            if e != self.CLI_KEYS_ONLY:
                update_main(section, e)

        # devices section
        key = ConfSectionKey.DEVICES.value
        section = data.get(ConfSectionKey.DEVICES.value)
        if not section:
            raise RuntimeError("No configuration section '{}' found!".format(key))
        if not isinstance(section, dict):
            raise RuntimeError("configuration section '{}' expected to be a dictionary!".format(key))
        for device_name, device_section in section.items():
            self._devices[device_name] = device_section

    def _parse_cli(self):
        parser = self.create_cli_parser()
        args = parser.parse_args()

        def handle_cli(key_enum, default_value=None):
            key = key_enum.value
            value = getattr(args, key, default_value)
            self._config[key] = value

        handle_cli(ConfMainKey.CONF_FILE, DEFAULT_CONFFILE)
        handle_cli(ConfMainKey.SYSTEMD)

        handle_cli(ConfMainKey.LOG_LEVEL)
        handle_cli(ConfMainKey.LOG_FILE)
        handle_cli(ConfMainKey.LOG_MAX_BYTES)
        handle_cli(ConfMainKey.LOG_MAX_COUNT)
        handle_cli(ConfMainKey.LOG_PRINT)

    @classmethod
    def create_cli_parser(cls):
        parser = ArgumentParser(
            description="Relay messages between Enocean (USB) and MQTT",
            add_help=True
        )

        parser.add_argument(
            "-c", "--" + ConfMainKey.CONF_FILE.value,
            help="config file path",
            default=DEFAULT_CONFFILE
        )
        parser.add_argument(
            "-f", "--" + ConfMainKey.LOG_FILE.value,
            help="log file (if stated journal logging ist disabled)"
        )
        parser.add_argument(
            "-l", "--" + ConfMainKey.LOG_LEVEL.value,
            choices=["debug", "info", "warning", "error"],
            help="set log level"
        )
        parser.add_argument(
            "-p", "--" + ConfMainKey.LOG_PRINT.value,
            action="store_true",
            default=None,
            help="print log output to console too"
        )
        parser.add_argument(
            "-s", "--" + ConfMainKey.SYSTEMD.value,
            action="store_true",
            default=None,
            help="systemd/journald integration (skip timestamp + prints to console)"
        )

        return parser

    @classmethod
    def get(cls, config, key_enum, default=None):
        key = key_enum.value
        return config.get(key, default)

    @classmethod
    def get_str(cls, config, key_enum, default=None):
        key = key_enum.value
        value = config.get(key)
        if value is None:  # value could be inserted by CLI as None so dict.default doesn't work
            value = default

        if value != default and not isinstance(value, str):
            raise ValueError(f"expected type 'str' for '{key}'!")

        return value

    @classmethod
    def get_bool(cls, config, key_enum, default=None):
        key = key_enum.value
        value = config.get(key)

        if not isinstance(value, bool):
            if value is None:
                value = default
            else:
                temp = str(value).lower().strip()
                if temp in ["true", "1", "on", "active"]:
                    value = True
                elif temp in ["false", "0", "off", "inactive"]:
                    value = False

        if value != default and not isinstance(value, bool):
            raise ValueError(f"expected type 'bool' for '{key}'!")

        return value

    @classmethod
    def get_int(cls, config, key_enum, default=None):
        key = key_enum.value
        value = config.get(key)

        if not isinstance(value, int):
            if value is None:
                value = default
            else:
                try:
                    value = int(value, 0)  # auto convert hex
                except ValueError:
                    print("cannot parse {} ({}) as int!".format(key, value))

        if value != default and not isinstance(value, int):
            raise ValueError(f"expected type 'int' for '{key}'!")

        return value

    @classmethod
    def get_loglevel(cls, config, key_enum, default=logging.INFO):
        key = key_enum.value
        value = config.get(key)

        if not isinstance(value, type(logging.INFO)):
            input_value = str(value).lower().strip() if value is not None else value
            if input_value == "debug":
                value = logging.DEBUG
            elif input_value == "info":
                value = logging.INFO
            elif input_value == "warning":
                value = logging.WARNING
            elif input_value == "error":
                value = logging.ERROR
            else:
                if input_value is not None:
                    print("cannot parse {} ({})!".format(key, input_value))
                value = default

        return value
