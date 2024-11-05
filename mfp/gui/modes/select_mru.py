
#! /usr/bin/env python
'''
select_mru.py: SelectMRUMode minor mode

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode

from mfp.gui_main import MFPGUI


class SelectMRUMode (InputMode):

    mru_list = []
    touch_enabled = True

    def __init__(self, window):
        self.manager = window.input_mgr
        self.window = window
        self.keyhandler = self.window.stage.connect("key-release-event", self.key_release)

        InputMode.__init__(self, "Select Most-Recent")

        SelectMRUMode.touch_enabled = False
        self.select_next()

        self.select_cbid = self.window.signal_listen("select", self.touch)
        self.remove_cbid = self.window.signal_listen("remove", self.forget)

    @classmethod
    def init_bindings(cls):
        cls.bind("C-TAB", cls.select_next, "Select most-recent element")

    async def select_next(self):
        try:
            curloc = SelectMRUMode.mru_list.index(self.window.selected)
        except:
            curloc = len(SelectMRUMode.mru_list)

        if curloc < len(SelectMRUMode.mru_list) - 1:
            newloc = curloc + 1
        else:
            newloc = 0
        await self.window.select(SelectMRUMode.mru_list[newloc])
        return True

    def key_release(self, stage, event):
        if event.keyval == 66:
            SelectMRUMode.touch_enabled = True
            SelectMRUMode.touch(self.window, "select", self.window.selected)
            self.window.stage.disconnect(self.keyhandler)
            self.window.input_mgr.disable_minor_mode(self)

    def disable(self): 
        self.window.signal_unlisten(self.select_cbid)
        self.select_cbid = None 
        self.window.signal_unlisten(self.remove_cbid)
        self.remove_cbid = None 

    @classmethod
    def touch(self, window, signal, obj):
        if SelectMRUMode.touch_enabled:
            if obj in SelectMRUMode.mru_list:
                SelectMRUMode.mru_list.remove(obj)
            SelectMRUMode.mru_list[:0] = [obj]

    @classmethod
    def forget(self, window, signal, obj):
        if obj in SelectMRUMode.mru_list:
            SelectMRUMode.mru_list.remove(obj)
