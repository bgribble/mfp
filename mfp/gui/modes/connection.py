#! /usr/bin/env python2.6
'''
connection.py: ConnectionMode minor mode 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from ..input_mode import InputMode
from ..connection_element import ConnectionElement 

from mfp import MFPGUI 

class ConnectionMode (InputMode):
	def __init__(self, window, endpoint, connect_rev=False):
		self.manager = window.input_mgr
		self.window = window 
		self.reverse = connect_rev
		
		self.source_obj = None
		self.source_port = 0 
		self.dest_obj = None
		self.dest_port = 0 

		if self.reverse:
			self.dest_obj = endpoint
		else:
			self.source_obj = endpoint 

		InputMode.__init__(self, "ConnectionMode")

		self.bind("RET", self.make_connection, "connection-commit")
		self.bind("ESC", self.abort_connection, "connection-rollback")

		self.bind("0", lambda: self.set_port_key(0), "connection-to-port-0")
		self.bind("1", lambda: self.set_port_key(1), "connection-to-port-1")
		self.bind("2", lambda: self.set_port_key(2), "connection-to-port-2")
		self.bind("3", lambda: self.set_port_key(3), "connection-to-port-3")
		self.bind("4", lambda: self.set_port_key(4), "connection-to-port-4")
		self.bind("5", lambda: self.set_port_key(5), "connection-to-port-5")
		self.bind("6", lambda: self.set_port_key(6), "connection-to-port-6")
		self.bind("7", lambda: self.set_port_key(7), "connection-to-port-7")
		self.bind("8", lambda: self.set_port_key(8), "connection-to-port-8")
		self.bind("9", lambda: self.set_port_key(9), "connection-to-port-9")

	def make_connection(self):
		# are both ends selected?
		if self.reverse and self.source_obj is None and self.window.selected:
			self.source_obj = self.window.selected 

		if not self.reverse and self.dest_obj is None and self.window.selected:
			self.dest_obj = self.window.selected 

		if self.source_obj and self.dest_obj:
			print "Making connection:"
			print self.source_obj, self.source_port, '-->', self.dest_obj, self.dest_port

			if MFPGUI().mfp.connect(self.source_obj.obj_id, self.source_port,
					  		        self.dest_obj.obj_id, self.dest_port):
				c = ConnectionElement(self.window, self.source_obj, self.source_port,
									  self.dest_obj, self.dest_port)
				self.source_obj.connections_out.append(c)
				self.dest_obj.connections_in.append(c)
			else:
				print "Cannot make connection"

		self.manager.disable_minor_mode(self)	
		return True 

	def abort_connection(self):
		print "Aborting connection"
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
		return True 

		
