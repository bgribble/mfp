#! /usr/bin/env python2.6
'''
gui.py
GTK/clutter gui for MFP -- main thread

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading 
from request import Request
from singleton import Singleton

class MFPGUI (object):
	__metaclass__ = Singleton

	def __init__(self, q):
		from mfp.gtk.patch_window import PatchWindow
		self.cmd_pipe = q
		self.cmd_thread = threading.Thread(target=self.reader_thread)
		self.cmd_pipe.init_slave(reader=False)

		self.appwin = PatchWindow()
		self.quit_request = False

		
	def reader_thread(self):
		while not self.quit_request:
			qcmd = self.cmd_pipe.get()
			if not qcmd:
				pass 
			elif qcmd.payload == 'quit':
				self.quit_request = True
			else:
				self.incoming_cmd(qcmd)
		self.appwin.destroy()

	def incoming_cmd(self, req):
		from .gtk.processor_element import ProcessorElement
		from .gtk.message_element import MessageElement
		from .gtk.text_element import TextElement

		cmd = req.payload.get('cmd')
		args = req.payload.get('args')

		if cmd == 'create':
			ctors = {
				'processor': ProcessorElement,
				'message': MessageElement,
				'text': TextElement
			}
			prms = args.get('gui_params', {})
			etype = prms.get('element_type')
			ctor = ctors.get(etype)
			if ctor:
				o = ctor(self.appwin, prms.get('position_x', 0), prms.get('position_y', 0))
				o.obj_id = args.get('obj_id')
				o.configure(prms)
		elif cmd == 'connect':
			pass
		elif cmd == 'clear':
			pass

	def mfp_send(self, obj, callback=None):
		req = Request(obj, callback=callback)
		self.cmd_pipe.put(req)
		return req 

	def create(self, name, args=''):
		r = self.mfp_send(dict(cmd="create", args=dict(type=name, args=args)))
		self.cmd_pipe.wait(r)
		print "gui create got", r.response
		return r.response

	def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		r = self.mfp_send(dict(cmd="connect", 
						         args=dict(obj_1_id=obj_1_id, obj_1_port=obj_1_port,
						                   obj_2_id=obj_2_id, obj_2_port=obj_2_port)))
		self.cmd_pipe.wait(r)
		return r.response

	def disconnect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		r = self.mfp_send(dict(cmd="disconnect", 
						         args=dict(obj_1_id=obj_1_id, obj_1_port=obj_1_port,
						                   obj_2_id=obj_2_id, obj_2_port=obj_2_port)))
		self.cmd_pipe.wait(r)
		return r.response

	def delete(self, obj_id):
		r = self.mfp_send(dict(cmd="delete", args=dict(obj_id=obj_id)))
		self.cmd_pipe.wait(r)
		return r.response 

	def send_bang(self, obj_id, port):
		r = self.mfp_send(dict(cmd="send_bang", args=dict(obj_id=obj_id, port=port)))
		self.cmd_pipe.wait(r)
		return r.response 

	def send_params(self, obj_id, params):
		r = self.mfp_send(dict(cmd="gui_params", args=dict(obj_id=obj_id, params=params)))
		self.cmd_pipe.wait(r)
		return r.response 

	def start_main(self):
		import clutter 
		self.cmd_thread.start()
		clutter.main()
		if not self.quit_request:
			self.mfp_send('quit')

def main(gui_queue):
	print "MFPGUI: creating gui slave"
	guiapp = MFPGUI(gui_queue)
	guiapp.start_main()
