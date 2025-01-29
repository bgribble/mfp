#! /usr/bin/env python
'''
key_sequencer.py: Collect modifiers and key/mouse clicks into Emacs-like strings

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from mfp import log
from . import key_defs

from .event import (
    ButtonPressEvent,
    ButtonReleaseEvent,
    KeyPressEvent,
    KeyReleaseEvent,
    MotionEvent,
    ScrollEvent
)


class KeySequencer (object):
    def __init__(self):
        self.mouse_buttons = set()
        self.mod_keys = set()

        self.sequences = []

    def pop(self):
        if len(self.sequences) > 0:
            rval = self.sequences[0]
            self.sequences[:1] = []
            return rval
        return None

    def process(self, event):
        # KEY PRESS
        if isinstance(event, KeyPressEvent):
            code = event.keyval
            if code in key_defs.MOD_ALL:
                if code in (key_defs.MOD_SHIFTALT, key_defs.MOD_SHIFTRALT):
                    self.mod_keys.add(key_defs.MOD_SHIFT)
                    self.mod_keys.add(key_defs.MOD_ALT)
                else:
                    self.mod_keys.add(code)
            else:
                self.sequences.append(self.canonicalize(event))

        # KEY RELEASE
        elif isinstance(event, KeyReleaseEvent):
            code = event.keyval
            if code in key_defs.MOD_ALL:
                try:
                    if code in (key_defs.MOD_SHIFTALT, key_defs.MOD_SHIFTRALT):
                        if key_defs.MOD_SHIFT in self.mod_keys:
                            self.mod_keys.remove(key_defs.MOD_SHIFT)
                        if key_defs.MOD_ALT in self.mod_keys:
                            self.mod_keys.remove(key_defs.MOD_ALT)
                    elif code in self.mod_keys:
                        self.mod_keys.remove(code)
                except KeyError:
                    pass

        # BUTTON PRESS, BUTTON RELEASE, MOUSE MOTION
        elif isinstance(event, (
            ButtonPressEvent, ButtonReleaseEvent, MotionEvent, ScrollEvent
        )):
            self.sequences.append(self.canonicalize(event))

    def canonicalize(self, event):
        key = ''

        if (key_defs.MOD_CTRL in self.mod_keys) or (key_defs.MOD_RCTRL in self.mod_keys):
            key += 'C-'
        if (key_defs.MOD_ALT in self.mod_keys) or (key_defs.MOD_RALT in self.mod_keys):
            key += 'A-'
        if (key_defs.MOD_WIN in self.mod_keys) or (key_defs.MOD_RWIN in self.mod_keys):
            key += 'W-'

        if isinstance(event, str):
            if (key_defs.MOD_SHIFT in self.mod_keys) or (key_defs.MOD_RSHIFT in self.mod_keys):
                key = 'S-' + key
            return key + event

        if isinstance(event, (KeyPressEvent, KeyReleaseEvent)):
            ks = event.keyval

            # FIXME - shifted unicode keys
            if (
                ks and ks >= 256
                and ((key_defs.MOD_SHIFT in self.mod_keys)
                     or (key_defs.MOD_RSHIFT in self.mod_keys))
            ):
                key = 'S-' + key

            if ks in (key_defs.KEY_TAB, key_defs.KEY_SHIFTTAB):
                key += 'TAB'
            elif ks == key_defs.KEY_UP:
                key += 'UP'
            elif ks == key_defs.KEY_DN:
                key += 'DOWN'
            elif ks == key_defs.KEY_LEFT:
                key += 'LEFT'
            elif ks == key_defs.KEY_RIGHT:
                key += 'RIGHT'
            elif ks == key_defs.KEY_ENTER:
                key += 'RET'
            elif ks == key_defs.KEY_ESC:
                key += 'ESC'
            elif ks == key_defs.KEY_DEL:
                key += 'DEL'
            elif ks == key_defs.KEY_BKSP:
                key += 'BS'
            elif ks == key_defs.KEY_INS:
                key += 'INS'
            elif ks == key_defs.KEY_PGUP:
                key += 'PGUP'
            elif ks == key_defs.KEY_PGDN:
                key += 'PGDN'
            elif not ks or ks < 256:
                if event.unicode and event.unicode.islower():
                    if (key_defs.MOD_SHIFT in self.mod_keys) or (key_defs.MOD_RSHIFT in self.mod_keys):
                        key += event.unicode.upper()
                    else:
                        key += event.unicode
                else:
                    key += event.unicode
            else:
                log.debug("unhandled keycode", ks)
                key += "%d" % ks
            return key

        if isinstance(event, (ButtonPressEvent, ButtonReleaseEvent)):
            button = event.button
            clicks = event.click_count

            prefix = ''
            if (key_defs.MOD_SHIFT in self.mod_keys) or (key_defs.MOD_RSHIFT in self.mod_keys):
                prefix = 'S-'

            key += f"{prefix}M{button}"

            if clicks == 2:
                key += "DOUBLE"
            elif clicks == 3:
                key += "TRIPLE"

            if isinstance(event, ButtonPressEvent):
                key += 'DOWN'
                self.mouse_buttons.add(button)
            else:
                key += 'UP'
                if button in self.mouse_buttons:
                    self.mouse_buttons.remove(button)

        elif isinstance(event, MotionEvent):
            prefix = ''
            if (key_defs.MOD_SHIFT in self.mod_keys) or (key_defs.MOD_RSHIFT in self.mod_keys):
                prefix = 'S-'

            for b in (1, 2, 3):
                if b in self.mouse_buttons:
                    key += f'{prefix}M{b}-'
            key += 'MOTION'

        elif isinstance(event, ScrollEvent):
            if abs(event.dy) < 0.1:
                key = ''
            else:
                for b in (1, 2, 3):
                    if b in self.mouse_buttons:
                        key += 'M%d-' % b
                key += 'SCROLL'
                if event.smooth:
                    key += 'SMOOTH'
                if event.dy > 0.001:
                    key += 'DOWN'
                elif event.dy < -0.001:
                    key += 'UP'

        return key
