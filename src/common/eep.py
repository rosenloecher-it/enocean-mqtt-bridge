import copy


class Eep:
    """
    EnOcean Equipment Profiles (EEP)
    """

    # noinspection PyShadowingBuiltins
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

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.rorg == other.rorg and self.func == other.func and self.type == other.type and \
               self.direction == other.direction and self.command == other.command

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.__class__.__name__, self.rorg, self.func, self.type, self.direction, self.command))
