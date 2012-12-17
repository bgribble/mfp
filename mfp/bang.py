

class BangType (object):
    def __repr__(self):
        return "Bang"

    @classmethod
    def load(klass, objdict):
        return Bang


class UninitType (object):
    def __repr__(self):
        return "Uninit"

    @classmethod
    def load(klass, objdict):
        return Uninit

Bang = BangType()
Uninit = UninitType()
