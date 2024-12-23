#! /usr/bin/env python
'''
label_edit.py: Minor mode for editing contents of a label

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import asyncio
from mfp import log
from mfp.gui_main import MFPGUI
from mfp.trie import Trie
from ..input_mode import InputMode
from ..colordb import ColorDB


def editpoint(s1, s2, editpos=None):
    """
    Return the first point at which s1 and s2 differ, or
    the proposed editpoint if provided

    fooobar, foobar, 2 --> 2
    foobar, followme, 3 --> 2
    fooobar, foobar, None --> 3
    """
    l1 = len(s1)
    l2 = len(s2)
    if s1 == s2:
        return None
    for ept in range(min(l1, l2)):
        if s1[ept] != s2[ept] or editpos and ept == editpos:
            return ept
    return min(l1, l2)


class Blinker:
    """
    Blinks the cursor in a text widget
    """
    def __init__(self, blink_time=0.5):
        self.blink_time = 0.5
        self.tasks = {}

    def set_cursor(self, widget, val):
        widget.set_cursor_visible(val)

    async def run(self, widget):
        cursor = True
        while True:
            self.set_cursor(widget, cursor)
            cursor = not cursor
            await asyncio.sleep(self.blink_time)

    def start(self, widget):
        if widget not in self.tasks:
            self.tasks[widget] = MFPGUI().async_task(self.run(widget))

    def stop(self, widget):
        if widget in self.tasks:
            self.tasks[widget].cancel()
            del self.tasks[widget]
        self.set_cursor(widget, False)


class LabelEditMode (InputMode):
    def __init__(
        self, window, element, label, multiline=False, markup=False,
        mode_desc="Edit text", initial=None, completions=None, history=None
    ):
        self.window = window
        self.manager = window.input_mgr
        self.element = element
        self.widget = label
        self.multiline = multiline
        self.markup = markup
        self.text = initial if initial else self.widget.get_text()
        self.cursor_color = ColorDB().find("default-text-cursor-color")
        self.undo_stack = [(self.text, len(self.text))]
        self.undo_pos = -1
        self.activate_handler_id = None
        self.text_changed_handler_id = None
        self.key_focus_out_handler_id = None
        self.key_press_handler_id = None
        self.editpos = 0
        self.selection_start = 0
        self.selection_end = 0
        self.blinker = Blinker()
        self.completions = completions
        self.completions_cache = []
        self.history = history
        self.history_root = ''
        self.history_cache = []
        self.history_position = None

        InputMode.__init__(self, mode_desc)

    @classmethod
    def init_bindings(cls):
        cls.bind("label-enter-key", cls.enter_key, "Accept edits", "RET", )
        cls.bind("label-accept-edits", cls.commit_edits, "Accept edits", "C-RET",
                 menupath="Context > Accept edits")
        cls.bind("label-discard-edits", cls.rollback_edits, "Discard edits", "ESC",
                 menupath="Context > Discard edits")
        cls.bind("label-cursor-left", cls.move_left, "Move cursor left", "LEFT", )
        cls.bind("label-cursor-right", cls.move_right, "Move cursor right", "RIGHT", )
        cls.bind("label-cursor-up", cls.move_up, "Move cursor up one line", "UP", )
        cls.bind("label-cursor-down", cls.move_down, "Move cursor down one line", "DOWN", )
        cls.bind("label-select-left", cls.select_left, "Grow/shrink selection left", "S-LEFT", )
        cls.bind("label-select-right", cls.select_right, "Grow/shrink selection right", "S-RIGHT", )
        cls.bind("label-select-up", cls.select_up, "Grow/shrink selection up one line", "S-UP", )
        cls.bind("label-select-down", cls.select_down, "Gro/shrink selection down one line", "S-DOWN", )
        cls.bind("label-delete-left", cls.delete_left, "Delete to the left", "BS", )
        cls.bind("label-delete-right", cls.delete_right, "Delete to the right", "DEL", )
        cls.bind("label-select-all", cls.select_all, "Select all text", "C-a",
                 menupath="Context > Select all")
        cls.bind("label-undo-typing", cls.undo_edit, "Undo typing", "C-z",
                 menupath="Context > Undo typing")
        cls.bind("label-redo-typing", cls.redo_edit, "Redo typing", "C-r",
                 menupath="Context > Redo typing")
        cls.bind("label-cut", cls.cut, "Cut selection into clipboard", "C-x",
                 menupath="Context > Cut")
        cls.bind("label-copy", cls.copy, "Copy selection into clipboard", "C-c",
                 menupath="Context > Copy")
        cls.bind("label-paste", cls.paste, "Paste from clipboard into label", "C-v",
                 menupath="Context > Paste")
        cls.bind("label-tab-complete", cls.complete, "Complete entry", "TAB")
        cls.bind("label-insert-text", cls.insert_text, "Insert text", None)

    async def setup(self):
        inittxt = await self.element.label_edit_start()
        if inittxt:
            self.text = inittxt

        self.update_label(raw=True)

        self.start_editing()
        self.update_cursor()
        self.set_selection(0, len(self.text))

        await super().setup()

    def complete(self):
        if not self.completions:
            return False

        # if there are completions, cycle through them
        if self.completions_cache:
            comp = self.completions_cache[0]
            all_completions = self.completions_cache[1:] + [comp]
            self.text = comp
            self.editpos = len(self.text)
            self.set_selection(self.editpos, self.editpos)
            self.completions_cache = all_completions
            return True

        candidates, root = self.completions.find(self.text)
        if candidates:
            if self.text not in candidates:
                candidates.append(self.text)
            self.text = root
            self.editpos = len(self.text)
            self.set_selection(self.editpos, self.editpos)
            self.completions_cache = candidates
        return True

    def enter_key(self):
        if self.multiline:
            return self.insert_text("\n")
        return self.commit_edits()

    def cut(self):
        sel = self.text[self.selection_start:self.selection_end]
        self.window.clipboard_set(sel)
        self.delete_selection()
        return True

    def copy(self):
        sel = self.text[self.selection_start:self.selection_end]
        self.window.clipboard_set(sel)
        return True

    def paste(self):
        newtext = self.window.clipboard_get()
        self.delete_selection()
        newtext = self.text[:self.editpos] + newtext + self.text[self.editpos:]
        self.text = newtext
        self.update_label(raw=True)
        self.set_selection(self.editpos, self.editpos + len(newtext))
        return True

    def set_selection(self, start, end):
        self.selection_start = start
        self.selection_end = end
        self.update_label(raw=True)
        self.widget.set_selection(start, end)
        return True

    def delete_selection(self):
        self.history_position = None
        if self.selection_start == self.selection_end:
            return True

        self.editpos = self.selection_start
        self.text = self.text[:self.selection_start] + self.text[self.selection_end:]
        self.update_label(raw=True)
        self.set_selection(self.editpos, self.editpos)
        return True

    def select_all(self):
        self.set_selection(0, len(self.text))
        self.editpos = 0
        return True

    def insert_text(self, keysym):
        if len(keysym) > 1:
            return False

        self.delete_selection()

        newtext = self.text[:self.editpos] + keysym + self.text[self.editpos:]
        self.text = newtext

        self.editpos += 1
        self.set_selection(self.editpos, self.editpos)
        return True

    def delete_left(self):
        if self.editpos == 0:
            return True

        if self.selection_start != self.selection_end:
            self.delete_selection()
            return True

        newtext = self.text[:self.editpos-1] + self.text[self.editpos:]
        self.text = newtext
        self.editpos -= 1
        self.update_label(raw=True)
        self.set_selection(self.editpos, self.editpos)
        return True

    def delete_right(self):
        if self.editpos == len(self.text):
            return True

        if self.selection_start != self.selection_end:
            self.delete_selection()
            return True

        newtext = self.text[:self.editpos] + self.text[self.editpos+1:]
        self.text = newtext
        self.update_label(raw=True)
        self.set_selection(self.editpos, self.editpos)
        return True

    def disable(self):
        self.end_editing()
        self.update_label(raw=False)
        return True

    def start_editing(self):
        def synth_ret(*args):
            self.manager.synthesize("RET")

        if self.multiline is False:
            self.widget.set_single_line_mode(True)
            self.activate_handler_id = self.widget.signal_listen("activate", synth_ret)
        else:
            self.widget.set_single_line_mode(False)

        self.text_changed_handler_id = self.widget.signal_listen("text-changed", self.text_changed)

        self.editpos = len(self.text)
        self.widget.set_cursor_color(self.cursor_color)
        self.widget.set_cursor_visible(True)
        self.update_cursor()
        self.widget.set_editable(True)

        if self.widget.blink_cursor:
            self.blinker.start(self.widget)
        return True

    def end_editing(self):
        self.widget.set_editable(False)
        self.widget.set_cursor_visible(False)
        if self.activate_handler_id:
            self.widget.signal_unlisten(self.activate_handler_id)
            self.widget.set_activatable(False)
            self.widget.set_single_line_mode(False)
            self.activate_handler_id = None
        if self.key_focus_out_handler_id:
            self.widget.signal_unlisten(self.key_focus_out_handler_id)
            self.key_focus_out_handler_id = None
        if self.text_changed_handler_id:
            self.widget.signal_unlisten(self.text_changed_handler_id)
            self.text_changed_handler_id = None
        if self.key_press_handler_id:
            MFPGUI().appwin.signal_unlisten(self.key_press_handler_id)
            self.key_press_handler_id = None

        if self.widget.blink_cursor:
            self.blinker.stop(self.widget)
        return True

    async def text_changed(self, widget, signal, old_text, new_text, *rest):
        if new_text == old_text:
            return True

        change_at = editpoint(old_text, new_text, self.editpos)
        change_dir = len(new_text) - len(old_text)
        if self.undo_pos < -1:
            self.undo_stack[self.undo_pos:] = []
            self.undo_pos = -1

        self.undo_stack.append((old_text, self.editpos))
        self.text = new_text

        editpos = self.widget.get_cursor_position()
        if editpos == -1:
            self.editpos = len(self.text)
        elif change_dir > 0:
            self.editpos = change_at + change_dir
        else:
            self.editpos = change_at

        if hasattr(self.element, "label_edit_changed"):
            await self.element.label_edit_changed(self.widget, self.text)
        return True

    async def commit_edits(self):
        self.text = self.widget.get_text()
        self.end_editing()
        self.update_label(raw=False)
        await self.element.label_edit_finish(self.widget, self.text)
        await self.element.end_edit()
        return True

    async def rollback_edits(self):
        txt, pos = self.undo_stack[0]
        self.text = txt or ''
        self.end_editing()
        self.update_label(raw=False)
        await self.element.label_edit_finish(self.widget, self.text)
        await self.element.end_edit()
        return True

    def move_to_start(self):
        self.editpos = 0
        self.set_selection(self.editpos, self.editpos)
        return True

    def move_to_end(self):
        self.editpos = len(self.text)
        self.set_selection(self.editpos, self.editpos)
        return True

    def move_left(self):
        self.editpos = max(self.editpos - 1, 0)
        self.set_selection(self.editpos, self.editpos)
        return True

    def select_left(self):
        orig_start = self.selection_start
        orig_end = self.selection_end

        new_editpos = max(self.editpos - 1, 0)

        if new_editpos < orig_start:
            new_start = new_editpos
            new_end = orig_end
        else:
            new_start = orig_start
            new_end = orig_end - 1

        self.editpos = new_editpos
        self.set_selection(
            new_start, new_end
        )
        return True

    def move_right(self):
        self.editpos = min(self.editpos + 1, len(self.text))
        self.set_selection(self.editpos, self.editpos)
        return True

    def select_right(self):
        orig_start = self.selection_start
        orig_end = self.selection_end

        new_editpos = min(self.editpos + 1, len(self.text))

        if new_editpos > orig_end:
            new_end = new_editpos
            new_start = orig_start
        else:
            new_end = orig_end
            new_start = orig_start + 1

        self.editpos = new_editpos
        self.set_selection(
            new_start, new_end
        )
        return True

    def _one_line_up(self, pos):
        if hasattr(self.widget, 'wrapped_text'):
            lines_above = self.widget.wrapped_text[:pos].split("\n")
        else:
            lines_above = self.text[:pos].split("\n")

        line_pos = len(lines_above[-1])
        if len(lines_above) > 2:
            return (
                sum(len(ll) + 1 for ll in lines_above[:-2])
                + min(len(lines_above[-2]), line_pos)
            )
        if len(lines_above) > 1:
            return min(len(lines_above[0]), line_pos)
        return 0

    def move_up(self):
        if self.multiline is False and self.history:
            if self.history_position is None:
                self.history_cache, _ = self.history.find(
                    self.text, sort_by=Trie.SORT_INSERT_ORDER
                )
                if self.history_cache:
                    self.history_root = self.text
                    self.history_position = 0
                    self.history_cache.append(self.text)
                else:
                    self.history_position = None
                    self.history_cache = []
            else:
                if self.history_position + 1 < len(self.history_cache):
                    self.history_position += 1
                else:
                    self.history_position = 0

            if self.history_position is not None:
                self.text = self.history_cache[self.history_position]
                self.editpos = len(self.text)
                self.set_selection(self.editpos, self.editpos)
                self.update_label(raw=True)
                return True

        self.editpos = self._one_line_up(self.editpos)
        self.set_selection(self.editpos, self.editpos)
        return True

    def select_up(self):
        if self.editpos == self.selection_start:
            new_start = self._one_line_up(self.selection_start)
            new_end = self.selection_end
            self.editpos = new_start
        else:
            new_start = self.selection_start
            new_end = self._one_line_up(self.selection_end)
            self.editpos = new_end

            if new_end < self.selection_start:
                new_start = new_end
                new_end = self.selection_start
        self.set_selection(new_start, new_end)
        return True

    def _one_line_down(self, pos):
        if hasattr(self.widget, 'wrapped_text'):
            lines_above = self.widget.wrapped_text[:pos].split("\n")
            lines_below = self.widget.wrapped_text[pos:].split("\n")
        else:
            lines_above = self.text[:pos].split("\n")
            lines_below = self.text[pos:].split("\n")
        line_pos = len(lines_above[-1])
        line_start = pos

        if len(lines_below) > 1:
            return (
                line_start
                + len(lines_below[0])
                + 1
                + min(len(lines_below[1]), line_pos)
            )
        return len(self.text)

    def move_down(self):
        if self.multiline is False and self.history:
            if self.history_position is None:
                self.history_cache, _ = self.history.find(
                    self.text, sort_by=Trie.SORT_INSERT_ORDER
                )
                if self.history_cache:
                    self.history_root = self.text
                    self.history_position = 0
                    self.history_cache.append(self.text)
                else:
                    self.history_position = None
            else:
                if self.history_position - 1 >= 0:
                    self.history_position -= 1
                else:
                    self.history_position = len(self.history_cache) - 1

            if self.history_position is not None:
                self.text = self.history_cache[self.history_position]
                self.editpos = len(self.text)
                self.set_selection(self.editpos, self.editpos)
                self.update_label(raw=True)
                return True

        self.editpos = self._one_line_down(self.editpos)
        self.set_selection(self.editpos, self.editpos)
        return True

    def select_down(self):
        if self.editpos == self.selection_end:
            new_start = self.selection_start
            new_end = self._one_line_down(self.selection_end)
            self.editpos = new_end
        else:
            new_start = self._one_line_down(self.selection_start)
            new_end = self.selection_end
            self.editpos = new_start
            if new_start > self.selection_end:
                new_end = new_start
                new_start = self.selection_end
        self.set_selection(new_start, new_end)
        return True

    def undo_edit(self):
        if self.undo_pos == -1:
            self.undo_stack.append((self.text, self.editpos))
            self.undo_pos = -2
        if self.undo_pos > (-len(self.undo_stack)):
            self.text, self.editpos = self.undo_stack[self.undo_pos]
            self.undo_pos = max(-len(self.undo_stack), self.undo_pos - 1)
            self.update_label(raw=True)

        return True

    def redo_edit(self):
        if self.undo_pos < -1:
            self.undo_pos += 1
            self.text, self.editpos = self.undo_stack[self.undo_pos]
            self.update_label(raw=True)
        return True

    def update_cursor(self):
        self.widget.grab_focus()
        self.widget.set_cursor_position(self.editpos)

    def update_label(self, raw=True):
        if raw or self.markup is False:
            self.widget.set_text(self.text)
            self.widget.set_use_markup(False)
        else:
            self.widget.set_markup(self.text)
        self.update_cursor()
        self.completions_cache = []
        return True

