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


    def __add__(self, other):
        return self 

    def __mul__(self, other):
        return self 

    def __sub__(self, other):
        return self 

    def __div__(self, other):
        return self 

    def __pow__(self, other):
        return self 

    def __bool__ (self):
        return False 

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

