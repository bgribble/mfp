#! /usr/bin/env python2.6 
'''
dsp.py
Python main loop for DSP subprocess 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import mfpdsp

class MFPDSP (object):
	def __init__(self, q):
		self.objects = {} 
		self.obj_id = 0 
		self.cmd_pipe = q
		self.spcount = 0
		
		q.init_slave(reader=False)

	def start (self):
		# start JACK thread 
		mfpdsp.dsp_startup(1, 1)
		mfpdsp.dsp_enable()

		time_to_quit = False

		while not time_to_quit:
			qcmd = self.cmd_pipe.get()

			if not qcmd: 
				continue
			elif qcmd.payload == 'quit':
				time_to_quit = True
				print "dsp process got quit"
				continue

			self.command(qcmd)
		mfpdsp.dsp_shutdown()
		import sys
		sys.exit(0)
		print "out of dsp thread\n"
		return True

	def remember(self, obj):
		oi = self.obj_id
		self.obj_id += 1
		self.objects[oi] = obj
		return oi 

	def recall(self, obj_id):
		return self.objects.get(obj_id)

	def command(self, req):
		cmd = req.payload.get('cmd')
		args = req.payload.get('args')
		if cmd == 'create':
			obj = mfpdsp.proc_create(args.get('name'), args.get('inlets'), args.get('outlets'),
			   					     args.get('params'))
			req.response = self.remember(obj)
		elif cmd == "get_param":
			obj_id = args.get('obj_id')
			param = args.get('name')
			obj = self.recall(obj_id)
			if obj:
				req.response = mfpdsp.proc_getparam(obj, param)
		elif cmd == "set_param":
			obj_id = args.get('obj_id')
			param = args.get('name')
			value = args.get('value')
			obj = self.recall(obj_id)
			if obj:
				req.response = mfpdsp.proc_setparam(obj, param, value)
			self.spcount += 1
		elif cmd == "connect":
			src = self.recall(args.get('obj_id'))
			dst = self.recall(args.get('target'))
			mfpdsp.proc_connect(src, args.get('outlet'), dst, args.get('inlet'))
		elif cmd == "disconnect":
			src = self.recall(args.get('obj_id'))
			dst = self.recall(args.get('target'))
			mfpdsp.proc_disconnect(src, args.get('outlet'), dst, args.get('inlet'))

		self.cmd_pipe.put(req)

def main(dsp_queue):
	dspapp = MFPDSP(dsp_queue)
	dspapp.start()

