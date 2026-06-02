"""
Helper class for representing parameter and style variables
"""

from carp.serializer import Serializable
from mfp import log

class ParamInfo(Serializable):
    def __init__(self, *args, **kwargs):
        self.label = kwargs.pop("label", "")
        self.editable = kwargs.pop("editable", True)
        self.show = kwargs.pop("show", False)
        self.null = kwargs.pop("null", False)
        self.tooltip = kwargs.pop("tooltip", "")
        self.choices = kwargs.pop("choices", None)
        self.param_type = kwargs.pop("param_type", str)
        self.extra_args = kwargs

        super().__init__()

    def to_dict(self):
        props = {
            s: getattr(self, s) for s in [
                "label", "editable", "show", "null", "tooltip", "choices", "extra_args"
            ]
        }
        props["param_type"] = self.param_type.__name__
        if callable(self.choices):
            log.error(f"Choices cannot be callable in a Property: {self}")
        return props

    @classmethod
    def from_dict(cls, values):
        if "param_type" in values:
            values["param_type"] = eval(values["param_type"])
        obj = cls(**values)
        return obj

class BitArray (tuple):
    pass

class PyLiteral (str):
    pass


class ListOfInt(list):
    pass


class ListOfPairs(list):
    pass


class DictOfRGBAColor(dict):
    pass


class DictOfProperty(dict):
    pass


class CodeBlock (str):
    pass
