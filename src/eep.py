import copy


class Eep:
    """
    EnOcean Equipment Profiles (EEP)
    """

    def __init__(self, rorg=None, func=None, type=None, direction=None, command=None):
        self.rorg = rorg
        self.func = func
        self.type = type
        self.direction = direction
        self.command = command

    def clone(self):
        return copy.deepcopy(self)

    def __str__(self):
        return "{:02x}-{:02x}-{:02x}".format(self.rorg, self.func, self.type)

    def __repr__(self) -> str:
        return "{}({:02x}-{:02x}-{:02x})".format(self.__class__.__name__, self.rorg, self.func, self.type)
