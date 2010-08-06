#! /usr/bin/env python2.6
'''
gui.py
GTK/clutter gui for MFP -- main thread

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading 
from request import Request

class MFPGUI (object):
	_instance = None 

	def __init__(self, q):
		from mfp.gtk.patch_window import PatchWindow
		self.cmd_pipe = q
		self.cmd_thread = threading.Thread(target=self.reader_thread)
		self.cmd_pipe.init_slave(reader=False)

		self.appwin = PatchWindow()
		self.quit_request = False

		MFPGUI._instance = self 
		
	def reader_thread(self):
		while not self.quit_request:
			qcmd = self.cmd_pipe.get()
			if not qcmd:
				pass 
			elif qcmd.payload == 'quit':
				self.quit_request = True
		
		self.appwin.destroy()

	@classmethod 
	def mfp_send(klass, obj, callback=None):
		req = Request(obj, callback=callback)
		MFPGUI._instance.cmd_pipe.put(req)
		return req 

	@classmethod 
	def create(klass, name, args):
		r = MFPGUI.mfp_send(dict(cmd="create", args=dict(type=name, args=args)))
		MFPGUI._instance.cmd_pipe.wait(r)
		return r.response

	@classmethod
	def connect(klass, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		r = MFPGUI.mfp_send(dict(cmd="connect", 
						         args=dict(obj_1_id=obj_1_id, obj_1_port=obj_1_port,
						                   obj_2_id=obj_2_id, obj_2_port=obj_2_port)))
		MFPGUI._instance.cmd_pipe.wait(r)
		return r.response

	@classmethod
	def disconnect(klass, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
		r = MFPGUI.mfp_send(dict(cmd="disconnect", 
						         args=dict(obj_1_id=obj_1_id, obj_1_port=obj_1_port,
						                   obj_2_id=obj_2_id, obj_2_port=obj_2_port)))
		MFPGUI._instance.cmd_pipe.wait(r)
		return r.response

	@classmethod
	def delete(klass, obj_id):
		r = MFPGUI.mfp_send(dict(cmd="delete", args=dict(obj_id=obj_id)))
		MFPGUI._instance.cmd_pipe.wait(r)
		return r.response 

	@classmethod
	def send_bang(klass, obj_id, port):
		r = MFPGUI.mfp_send(dict(cmd="send_bang", args=dict(obj_id=obj_id, port=port)))
		MFPGUI._instance.cmd_pipe.wait(r)
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
