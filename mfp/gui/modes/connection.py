#! /usr/bin/env python2.6
'''
connection.py: ConnectionMode minor mode

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode
from ..connection_element import ConnectionElement

from mfp import MFPGUI
from mfp import log


class ConnectionMode (InputMode):
    def __init__(self, window, endpoint, connect_rev=False):
        self.manager = window.input_mgr
        self.window = window
        self.reverse = connect_rev

        self.connection = None
        self.select_cbid = None 

        self.source_obj = None
        self.source_port = 0
        self.dest_obj = None
        self.dest_port = 0

        if self.reverse:
            self.dest_obj = endpoint
        else:
            self.source_obj = endpoint

        InputMode.__init__(self, "Connect")

        self.bind("RET", self.make_connection, "Accept connection")
        self.bind("ESC", self.abort_connection, "Discard connection")

        self.bind("C-p", self.get_port_key, "Enter port to connect")
        self.bind("0", lambda: self.set_port_key(0), "Connect port 0")
        self.bind("1", lambda: self.set_port_key(1), "Connect port 1")
        self.bind("2", lambda: self.set_port_key(2), "Connect port 2")
        self.bind("3", lambda: self.set_port_key(3), "Connect port 3")
        self.bind("4", lambda: self.set_port_key(4), "Connect port 4")
        self.bind("5", lambda: self.set_port_key(5), "Connect port 5")
        self.bind("6", lambda: self.set_port_key(6), "Connect port 6")
        self.bind("7", lambda: self.set_port_key(7), "Connect port 7")
        self.bind("8", lambda: self.set_port_key(8), "Connect port 8")
        self.bind("9", lambda: self.set_port_key(9), "Connect port 9")

        self.select_cbid = self.window.add_callback("select", self.select)

    def update_connection(self): 
        if (self.source_obj is None or self.dest_obj is None):
            if self.connection:
                self.connection.delete()
                self.connection = None 
            return True 

        if self.connection is None:
            self.connection = ConnectionElement(self.window, 
                                                self.source_obj, self.source_port,
                                                self.dest_obj, self.dest_port, 
                                                dashed=True)
            self.source_obj.connections_out.append(self.connection)
            self.dest_obj.connections_in.append(self.connection)
        else: 
            if self.connection.obj_1 and self.connection.obj_1 != self.source_obj:
                if self.connection in self.connection.obj_1.connections_out:
                    self.connection.obj_1.connections_out.remove(self.connection)
                self.source_obj.connections_out.append(self.connection)
            
            if self.connection.obj_2 and self.connection.obj_2 != self.dest_obj:
                if self.connection in self.connection.obj_2.connections_in:
                    self.connection.obj_2.connections_in.remove(self.connection)
                self.dest_obj.connections_in.append(self.connection)

            self.connection.obj_1 = self.source_obj
            self.connection.obj_2 = self.dest_obj
            self.connection.port_1 = self.source_port
            self.connection.port_2 = self.dest_port 

            self.connection.draw()

    def select(self, obj):
        if self.reverse:
            if self.dest_obj is not None and obj and self.dest_obj != obj:
                self.source_obj = obj
        else: 
            if self.source_obj is not None and obj and self.source_obj != obj:
                self.dest_obj = obj

        self.update_connection()

    def disable(self):
        self.window.remove_callback(self.select_cbid)
        self.select_cbid = None
        if self.connection:
            self.connection.delete()

    def get_port_key(self): 
        def callback(txt): 
            self.set_port_key(int(txt))

        if ((self.dest_obj is not None) 
            or (self.window.selected is not None and self.window.selected != self.source_obj)):
            dirspec = "destination input"
        else: 
            dirspec = "source output"

        self.window.get_prompted_input("Enter %s port:" % dirspec, callback)
        return True 

    def make_connection(self):
        # are both ends selected?
        if self.reverse and self.source_obj is None and self.window.selected:
            self.source_obj = self.window.selected

        if not self.reverse and self.dest_obj is None and self.window.selected:
            self.dest_obj = self.window.selected

        if self.source_obj and self.dest_obj:
            if MFPGUI().mfp.connect(self.source_obj.obj_id, self.source_port,
                                    self.dest_obj.obj_id, self.dest_port):
                c = ConnectionElement(self.window, self.source_obj, self.source_port,
                                      self.dest_obj, self.dest_port)
                self.source_obj.connections_out.append(c)
                self.dest_obj.connections_in.append(c)
            else:
                log.debug("ConnectionMode: Cannot make connection")

        self.manager.disable_minor_mode(self)
        return True

    def abort_connection(self):
        log.debug("ConnectionMode: Aborting connection")
        self.manager.disable_minor_mode(self)
        return True

    def set_port_key(self, portnum):
        if self.reverse:
            if (self.source_obj is None and self.window.selected and
                    self.window.selected != self.dest_obj):
                self.source_obj = self.window.selected

            if self.source_obj is not None:
                self.source_port = portnum
            else:
                self.dest_port = portnum
        else:
            if (self.dest_obj is None and self.window.selected and
                    self.window.selected != self.source_obj):
                self.dest_obj = self.window.selected

            if self.dest_obj is not None:
                self.dest_port = portnum
            else:
                self.source_port = portnum
        self.update_connection()
        return True
