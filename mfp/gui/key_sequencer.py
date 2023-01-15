#! /usr/bin/env python
'''
key_sequencer.py: Collect modifiers and key/mouse clicks into Emacs-like strings

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from mfp import log
from gi.repository import Clutter
from . import key_defs


def get_key_unicode(ev):
    if ev.unicode_value:
        return ord(ev.unicode_value)
    else:
        v = Clutter.keysym_to_unicode(ev.keyval)
        return v


class KeySequencer (object):
    def __init__(self):
        self.mouse_buttons = set()
        self.mod_keys = set()

        self.sequences = []

    def pop(self):
        if len(self.sequences):
            rval = self.sequences[0]
            self.sequences[:1] = []
            return rval
        else:
            return None

    def process(self, event):
        # KEY PRESS
        if event.type == Clutter.EventType.KEY_PRESS:
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
        elif event.type == Clutter.EventType.KEY_RELEASE:
            code = event.keyval
            if code in key_defs.MOD_ALL:
                try:
                    if code in (key_defs.MOD_SHIFTALT, key_defs.MOD_SHIFTRALT):
                        self.mod_keys.remove(key_defs.MOD_SHIFT)
                        self.mod_keys.remove(key_defs.MOD_ALT)
                    else:
                        self.mod_keys.remove(code)
                except KeyError:
                    pass

        # BUTTON PRESS, BUTTON RELEASE, MOUSE MOTION
        elif event.type in (Clutter.EventType.BUTTON_PRESS, Clutter.EventType.BUTTON_RELEASE,
                            Clutter.EventType.MOTION, Clutter.EventType.SCROLL):
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

        if event.type in (Clutter.EventType.KEY_PRESS, Clutter.EventType.KEY_RELEASE):
            ks = event.keyval
            if ks >= 256 and ((key_defs.MOD_SHIFT in self.mod_keys) or (key_defs.MOD_RSHIFT in self.mod_keys)):
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
            elif ks < 256:
                kuni = get_key_unicode(event)
                if kuni < 32:
                    ks = chr(event.keyval)
                    if (key_defs.MOD_SHIFT in self.mod_keys) or (key_defs.MOD_RSHIFT in self.mod_keys):
                        log.debug("SHIFT in modifiers but below 256 (%s)" % kuni)
                        ks = ks.upper()
                    key += ks
                else:
                    key += chr(kuni)
            else:
                log.debug("unhandled keycode", ks)
                key += "%d" % ks
            return key

        if (key_defs.MOD_SHIFT in self.mod_keys) or (key_defs.MOD_RSHIFT in self.mod_keys):
            key = 'S-' + key

        if event.type in (Clutter.EventType.BUTTON_PRESS, Clutter.EventType.BUTTON_RELEASE):
            button = event.button
            clicks = event.click_count
            key += "M%d" % button

            if clicks == 2:
                key += "DOUBLE"
            elif clicks == 3:
                key += "TRIPLE"

            if event.type == Clutter.EventType.BUTTON_PRESS:
                key += 'DOWN'
                self.mouse_buttons.add(button)
            else:
                key += 'UP'
                self.mouse_buttons.remove(button)

        elif event.type == Clutter.EventType.MOTION:
            for b in (1, 2, 3):
                if b in self.mouse_buttons:
                    key += 'M%d-' % b
            key += 'MOTION'

        elif event.type == Clutter.EventType.SCROLL:
            for b in (1, 2, 3):
                if b in self.mouse_buttons:
                    key += 'M%d-' % b
            key += 'SCROLL'
            direction = event.direction
            if direction == Clutter.ScrollDirection.SMOOTH:
                delta = Clutter.Event.get_scroll_delta(event)
                if abs(delta.dy) > 0.001 and abs(delta.dy) < 0.2:
                    key += 'SMOOTH'

                if abs(delta.dy) <= .001:
                    pass
                elif delta.dy < 0:
                    direction = Clutter.ScrollDirection.UP
                else:
                    direction = Clutter.ScrollDirection.DOWN

            if direction == Clutter.ScrollDirection.DOWN:
                key += 'DOWN'
            elif direction == Clutter.ScrollDirection.UP:
                key += 'UP'

        return key
