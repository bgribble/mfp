"""
clutter/event.py -- utils for canonicalizing Clutter events
"""


from functools import wraps
from gi.repository import Clutter
from mfp import log
from mfp.gui_main import MFPGUI

from ..event import (
    ButtonPressEvent,
    ButtonReleaseEvent,
    EnterEvent,
    KeyPressEvent,
    KeyReleaseEvent,
    LeaveEvent,
    MotionEvent,
    ScrollEvent
)


def get_key_unicode(ev):
    if ev.unicode_value:
        return ev.unicode_value
    v = Clutter.keysym_to_unicode(ev.keyval)
    return chr(v)


def transform_event(clutter_event, mfp_target):

    if not clutter_event:
        return None

    if clutter_event.type == Clutter.EventType.BUTTON_PRESS:
        return ButtonPressEvent(
            target=mfp_target,
            button=clutter_event.button,
            click_count=clutter_event.click_count
        )

    if clutter_event.type == Clutter.EventType.BUTTON_RELEASE:
        return ButtonReleaseEvent(
            target=mfp_target,
            button=clutter_event.button,
            click_count=clutter_event.click_count
        )
    if clutter_event.type == Clutter.EventType.KEY_PRESS:
        return KeyPressEvent(
            target=mfp_target,
            keyval=clutter_event.keyval,
            unicode=get_key_unicode(clutter_event)
        )

    if clutter_event.type == Clutter.EventType.KEY_RELEASE:
        return KeyReleaseEvent(
            target=mfp_target,
            keyval=clutter_event.keyval,
            unicode=get_key_unicode(clutter_event)
        )

    if clutter_event.type == Clutter.EventType.MOTION:
        return MotionEvent(
            target=mfp_target,
            x=clutter_event.x,
            y=clutter_event.y
        )

    if clutter_event.type == Clutter.EventType.SCROLL:
        delta = Clutter.Event.get_scroll_delta(clutter_event)
        smooth = False
        if clutter_event.direction == Clutter.ScrollDirection.SMOOTH:
            smooth = True
        return ScrollEvent(
            target=mfp_target,
            smooth=smooth,
            dx=delta.dx,
            dy=delta.dy
        )

    # NOTE: the event.source is not reliable, at least not on my
    # machine with my GL setup. It sometimes comes up with a Clutter
    # object that is not visible, or is on the other edge of the screen.
    # enter/leave really only used for HOVER determination to show object
    # docs so it's OK that it is wrong  sometimes :/
    if clutter_event.type == Clutter.EventType.ENTER:
        if hasattr(mfp_target, 'event_sources'):
            source = mfp_target.event_sources.get(clutter_event.source)
            if not source and hasattr(clutter_event.source, 'container'):
                container = clutter_event.source.container
                source = mfp_target.event_sources.get(container)
                if not source and hasattr(container, 'container'):
                    container = container.container
                    source = mfp_target.event_sources.get(container)
            if not source:
                source = mfp_target

        else:
            source = mfp_target
        return EnterEvent(target=source)

    if clutter_event.type == Clutter.EventType.LEAVE:
        if hasattr(mfp_target, 'event_sources'):
            source = mfp_target.event_sources.get(clutter_event.source, mfp_target)
        else:
            source = mfp_target
        return LeaveEvent(target=source)

    return None


def repeat_event(target, signal_name):
    @wraps(repeat_event)
    def _inner(widget, *args):
        if len(args) == 0:
            MFPGUI().async_task(target.signal_emit(signal_name))
        else:
            event, *rest = args
            ev = transform_event(event, target)
            MFPGUI().async_task(target.signal_emit(signal_name, ev, *rest))
    return _inner
