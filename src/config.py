import logging
import os
from argparse import ArgumentParser

import yaml
from jsonschema import validate

DEFAULT_CONFFILE = "/etc/enocean_mqtt_bridge.conf"

CONFKEY_CONF_FILE = "conf_file"
CONFKEY_DEVICES = "devices"
CONFKEY_DEVICE_TYPE = "device_type"
CONFKEY_ENOCEAN_PORT = "enocean_port"
CONFKEY_LOG_FILE = "log_file"
CONFKEY_LOG_LEVEL = "log_level"
CONFKEY_LOG_MAX_BYTES = "log_max_bytes"
CONFKEY_LOG_MAX_COUNT = "log_max_count"
CONFKEY_LOG_PRINT = "log_print"
CONFKEY_MAIN = "main"
CONFKEY_SYSTEMD = "systemd"


CONFIG_MAIN_JSONSCHEMA = {
    "type": "object",
    "properties": {
        CONFKEY_ENOCEAN_PORT: {"type": "string", "minLength": 1},
    },
    "required": [
        CONFKEY_ENOCEAN_PORT
    ],
}


class Config:

    def __init__(self):
        self.config = {}

    @classmethod
    def load(cls):
        instance = Config()
        instance._parse_cli()
        instance._load_conf_file()

        return instance.config

    def _load_conf_file(self):
        conf_file = self.config[CONFKEY_CONF_FILE]
        if not os.path.isfile(conf_file):
            raise FileNotFoundError('config file ({}) does not exist!'.format(conf_file))
        with open(conf_file, 'r') as stream:
            file_data = yaml.unsafe_load(stream)

        def get_section(key):
            section = file_data.get(key)
            if not section:
                raise AttributeError("No configuration section '{}' found!".format(key))
            if not isinstance(section, dict):
                raise AttributeError("Configuration section '{}' expected to be a dictionary!".format(key))
            return section

        # main section
        main_section = get_section(CONFKEY_MAIN)
        validate(main_section, CONFIG_MAIN_JSONSCHEMA)
        self.config = {**main_section, **self.config}

        # devices section
        device_section = get_section(CONFKEY_DEVICES)
        devices = {}
        for device_name, device_config in device_section.items():
            devices[device_name] = device_config
        self.config[CONFKEY_DEVICES] = devices

    def _parse_cli(self):
        parser = self.create_cli_parser()
        args = parser.parse_args()

        def handle_cli(key, default_value=None):
            value = getattr(args, key, default_value)
            if value is not None:
                self.config[key] = value

        handle_cli(CONFKEY_CONF_FILE, DEFAULT_CONFFILE)
        handle_cli(CONFKEY_SYSTEMD)
        handle_cli(CONFKEY_LOG_LEVEL)
        handle_cli(CONFKEY_LOG_FILE)
        handle_cli(CONFKEY_LOG_MAX_BYTES)
        handle_cli(CONFKEY_LOG_MAX_COUNT)
        handle_cli(CONFKEY_LOG_PRINT)

    @classmethod
    def create_cli_parser(cls):
        parser = ArgumentParser(
            description="Relay messages between Enocean (USB) and MQTT",
            add_help=True
        )

        parser.add_argument(
            "-c", "--" + CONFKEY_CONF_FILE,
            help="config file path",
            default=DEFAULT_CONFFILE
        )
        parser.add_argument(
            "-f", "--" + CONFKEY_LOG_FILE,
            help="log file (if stated journal logging ist disabled)"
        )
        parser.add_argument(
            "-l", "--" + CONFKEY_LOG_LEVEL,
            choices=["debug", "info", "warning", "error"],
            help="set log level"
        )
        parser.add_argument(
            "-p", "--" + CONFKEY_LOG_PRINT,
            action="store_true",
            default=None,
            help="print log output to console too"
        )
        parser.add_argument(
            "-s", "--" + CONFKEY_SYSTEMD,
            action="store_true",
            default=None,
            help="systemd/journald integration (skip timestamp + prints to console)"
        )

        return parser

    @classmethod
    def get_str(cls, config, key, default=None):
        value = config.get(key)
        if value is None:  # value could be inserted by CLI as None so dict.default doesn't work
            value = default

        if value != default and not isinstance(value, str):
            raise ValueError(f"expected type 'str' for '{key}'!")

        return value

    @classmethod
    def get_bool(cls, config, key, default=None):
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
    def get_int(cls, config, key, default=None):
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
    def get_loglevel(cls, config, key, default=logging.INFO):
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
