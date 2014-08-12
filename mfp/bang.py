from .singleton import Singleton

class BangType (Singleton):
    def __repr__(self):
        return "Bang"

    @classmethod
    def load(klass, objdict):
        return Bang


class UninitType (Singleton):
    def __repr__(self):
        return "Uninit"

    @classmethod
    def load(klass, objdict):
        return Uninit

class UnboundType (Singleton):
    def __repr__(self):
        return "Unbound"

    @classmethod
    def load(klass, objdict):
        return Unbound

Bang = BangType()
Uninit = UninitType()
Unbound = UnboundType()

