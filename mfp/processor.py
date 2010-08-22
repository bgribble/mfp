#! /usr/bin/env python2.6 
'''
processor.py: Parent class of all processors 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from main import MFPApp 
from bang import Bang, Uninit

class Processor (object): 
	OK = 0
	ERROR = 1 

	def __init__(self, inlets, outlets, init_type, init_args):
		self.init_type = init_type
		self.init_args = init_args

		self.inlets = [ Uninit ] * inlets
		self.outlets = [ Uninit ] * outlets
		self.status = Processor.OK 
		self.obj_id = None

		# gui params are updated by the gui slave
		self.gui_params = {}

		# dsp_inlets and dsp_outlets are the processor inlet/outlet numbers 
		# of the ordinal inlets/outlets of the DSP object. 
		# for example dsp_outlets = [2] means processor outlet 2 
		# corresponds to outlet 0 of the underlying DSP object 
		self.dsp_obj = None 
		self.dsp_inlets = []
		self.dsp_outlets = [] 

		self.connections_out = [[] for r in range(outlets)]
		self.connections_in = [[] for r in range(inlets)]

	def delete(self):
		print "delete", self
		outport = 0
		for c in self.connections_out:
			for tobj, tport in c:
				self.disconnect(outport, tobj, tport)
			outport += 1

		inport = 0
		for c in self.connections_in:
			for tobj, tport in c:
				tobj.disconnect(tport, self, inport)
			inport += 1

		if self.dsp_obj is not None:
			print "calling dsp_delete"
			self.dsp_delete()

	def parse_args(self, argstring):
		if argstring == '' or argstring is None:
			return ()

		obj = eval(argstring)
		if not isinstance(obj, tuple):
			obj = (obj,)
		return obj

	def resize(self, inlets, outlets):
		if inlets > len(self.inlets):
			self.inlets += [ Uninit ] * inlets-len(self.inlets)
			self.connections_in += [[] for r in range(inlets-len(self.inlets)) ]
		else:
			for inlet in range(inlets, len(self.inlets)):
				for tobj, tport in self.connections_in[inlet]:
					tobj.disconnect(tport, self, inlet)
			self.inlets[inlets:] = []

		if outlets > len(self.outlets):
			self.outlets += [ Uninit ] * outlets-len(self.outlets)
			self.connections_out += [[] for r in range(outlets-len(self.outlets)) ]
		else:
			for outlet in range(outlets, len(self.outlets)):
				for tobj, tport in self.connections_out[outlet]:
					self.disconnect(outlet, tobj, tport)
			self.outlets[outlets:] = []
			self.connections_out[outlets:] = []

	def connect(self, outlet, target, inlet):
		# is this a DSP connection? 
		if outlet in self.dsp_outlets:
			self.dsp_connect(outlet, target, inlet)

		existing = self.connections_out[outlet]
		if (target,inlet) not in existing:
			existing.append((target,inlet))

		existing = target.connections_in[inlet]
		if (self,outlet) not in existing:
			existing.append((self,outlet))
		return True
	
	def disconnect(self, outlet, target, inlet):
		# is this a DSP connection? 
		if outlet in self.dsp_outlets:
			self.dsp_disconnect(outlet, target, inlet)

		existing = self.connections_out[outlet]
		if (target,inlet) in existing:
			existing.remove((target,inlet))

		existing = target.connections_in[inlet]
		if (self,outlet) in existing:
			existing.remove((self,outlet))
		return True

	def send(self, value, inlet=0):
		try:
			work = self._send(value, inlet)
			while len(work):
				w_target, w_val, w_inlet = work[0]
				work[:1] = w_target._send(w_val, w_inlet)
		except: 
			import traceback
			tb = traceback.format_exc()
			self.error(tb)

	def _send(self, value, inlet=0): 
		work = [] 
		self.inlets[inlet] = value

		if inlet == 0:
			self.outlets = [ Uninit ] * len(self.outlets)
			self.trigger()
			for conns, val in zip(self.connections_out, self.outlets):
				if val is not Uninit:
					for target, inlet in conns:
						work.append((target, val, inlet))
		return work 

	def error(self, tb=None):
		self.status = Processor.ERROR
		print "Error:", self
		if tb:
			print tb

	# save/restore helper
	def save(self):
		oinfo = {}
		oinfo['type'] = self.init_type
		oinfo['initargs'] = self.init_args
		oinfo['gui_params'] = self.gui_params
		conn = []
		for c in self.connections_out:
			conn.append([ (t[0].obj_id, t[1]) for t in c])
		oinfo['connections'] = conn
		return oinfo

	# 
	# DSP methods 
	# 

	def dsp_init(self, proc_name):
		self.dsp_obj = None 
		req = self.dsp_message("create", name=proc_name, inlets=len(self.dsp_inlets), 
					           outlets=len(self.dsp_outlets))
		MFPApp().wait(req)

	def dsp_response(self, request):
		if request.payload.get("cmd") == "create":
			self.dsp_obj = request.response

	def dsp_message(self, cmd, callback=None, **args):
		if callback is None:
			callback = self.dsp_response 
		payload = dict(cmd=cmd, args=args)
		return MFPApp().dsp_message(payload, callback=callback)

	def dsp_connect(self, outlet, target, inlet):
		self.dsp_message("connect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			             outlet=self.dsp_outlets.index(outlet), 
				         inlet=target.dsp_inlets.index(inlet)) 
		return True

	def dsp_disconnect(self, outlet, target, inlet):
		self.dsp_message("disconnect", obj_id=self.dsp_obj, target=target.dsp_obj, 
			             outlet=self.dsp_outlets.index(outlet), 
				         inlet=target.dsp_inlets.index(inlet)) 
		
	def dsp_setparam(self, name, value):
		req = self.dsp_message("set_param", obj_id=self.dsp_obj, name=name, value=value)
		MFPApp().wait(req)
		return req.response

	def dsp_delete(self):
		req = self.dsp_message("delete", obj_id=self.dsp_obj)
		MFPApp().wait(req)
		return req.response

	def dsp_getparam(self, name, callback=None):
		req = self.dsp_message("get_param", callback=callback, obj_id=self.dsp_obj, name=name) 
		MFPApp().wait(req)
		return req.response 

