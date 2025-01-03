from dataclasses import dataclass

@dataclass
class ButtonPressEvent:
    target: any = None
    button: int = 1
    click_count: int = 0

@dataclass
class ButtonReleaseEvent:
    target: any = None
    button: int = 1
    click_count: int = 0

@dataclass
class KeyPressEvent:
    target: any = None
    keyval: int = 0
    unicode: str = ''

@dataclass
class KeyReleaseEvent:
    target: any = None
    keyval: int = 0
    unicode: str = ''

@dataclass
class MotionEvent:
    target: any = None
    x: float = 0
    y: float = 0

@dataclass
class ScrollEvent:
    target: any = None
    smooth: bool = False
    dx: float = 0
    dy: float = 0

@dataclass
class FocusEvent:
    target: any = None
    focused: bool = False

@dataclass
class EnterEvent:
    target: any = None

@dataclass
class LeaveEvent:
    target: any = None

@dataclass
class PatchSelectEvent:
    target: any = None
