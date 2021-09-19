from typing import Optional

from src.device.base.base_enocean import BaseEnocean
from src.device.eltako.ffg7b_sensor import FFG7BSensor
from src.device.eltako.fsr61_actor import Fsr61Actor
from src.device.eltako.fud61_actor import Fud61Actor
from src.device.eltako.fud61_simple_switch import Fud61SimpleSwitch
from src.device.misc.log_device import LogEnocean
from src.device.misc.rocker_switch import RockerSwitch
from src.device.nodon.sin22_actor import Sin22Actor


class DeviceRegistry:
    """
    Translates device class import pathes (which are still possible) into normal strings. A former problem was, that
    refactorings affected config files. In this way the config names act like an alias.
    """
    __instance = None  # Here will be the instance stored.

    registry = {}  # type: dict[str, BaseEnocean.__class__]

    def __init__(self):
        """ Virtually private constructor. """
        if DeviceRegistry.__instance is not None:
            raise Exception("This class is a singleton!")

        DeviceRegistry.__instance = self

    @staticmethod
    def _instance():
        """ Static access method. """
        if DeviceRegistry.__instance is None:
            DeviceRegistry()
        return DeviceRegistry.__instance

    @classmethod
    def register(cls, key: str, device_type: BaseEnocean.__class__):
        if not key or not device_type:
            raise ValueError('invalid device registry data!')
        instance = cls._instance()
        instance.registry[key] = device_type

    @classmethod
    def get(cls, key) -> Optional[BaseEnocean.__class__]:
        instance = cls._instance()
        return instance.registry.get(key)


DeviceRegistry.register('EltakoFFG7B', FFG7BSensor)
DeviceRegistry.register('EltakoFsr61', Fsr61Actor)
DeviceRegistry.register('EltakoFud61', Fud61Actor)
DeviceRegistry.register('EltakoFud61SimpleSwitch', Fud61SimpleSwitch)
DeviceRegistry.register('NodonSin22', Sin22Actor)
DeviceRegistry.register('RockerSwitch', RockerSwitch)
DeviceRegistry.register('Sniffer', LogEnocean)
