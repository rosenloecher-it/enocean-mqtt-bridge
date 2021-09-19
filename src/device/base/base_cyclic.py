import abc

from src.device.base.base_device import BaseDevice


class BaseCyclic(BaseDevice):

    @abc.abstractmethod
    def check_cyclic_tasks(self):
        raise NotImplementedError

    def set_config(self, config):
        pass
