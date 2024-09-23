"""
Helper class for representing parameter and style variables
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParamInfo:
    label: str
    editable: Optional[bool] = True
    tooltip: Optional[str] = ""
    param_type: Optional[type] = str


class ListOfInt(list):
    pass
