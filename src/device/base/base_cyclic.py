import abc


class BaseCyclic(abc.ABC):

    @abc.abstractmethod
    def check_cyclic_tasks(self):
        raise NotImplementedError

    def set_config(self, config):
        pass
