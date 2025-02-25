"""
Helper class for representing parameter and style variables
"""
from dataclasses import dataclass, field, _MISSING_TYPE
from typing import Optional


@dataclass(slots=True, kw_only=True)
class ParamInfo:
    label: str
    editable: Optional[bool] = True
    show: Optional[bool] = False
    null: Optional[bool] = False
    tooltip: Optional[str] = ""
    choices: Optional[callable] = None
    param_type: Optional[type] = str
    extra_args: Optional[dict] = field(default_factory=dict)

    def __init__(self, *args, **kwargs):
        extra_kws = [k for k in kwargs if k not in self.__slots__]
        extra_args = {
            k: kwargs.pop(k)
            for k in extra_kws
        }
        for name, info in self.__dataclass_fields__.items():
            if name in kwargs:
                setattr(self, name, kwargs[name])
            elif not isinstance(info.default, _MISSING_TYPE):
                setattr(self, name, info.default)
            elif not isinstance(info.default_factory, _MISSING_TYPE):
                setattr(self, name, info.default_factory())
        self.extra_args = extra_args


class ListOfInt(list):
    pass

class ListOfPairs(list):
    pass

class DictOfRGBAColor(dict):
    pass

class CodeBlock (dict):
    pass
