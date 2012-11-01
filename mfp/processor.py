#! /usr/bin/env python2.6 
'''
processor.py: Parent class of all processors 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
from .dsp_slave import DSPObject
from .evaluator import Evaluator
from .method import MethodCall
from .bang import Uninit 

from mfp import log 

class Processor (object): 
	OK = 0
	ERROR = 1 
	gui_type = 'processor'
	hot_inlets = [0]

	def __init__(self, inlets, outlets, init_type, init_args):
		from .main import MFPApp 
		self.init_type = init_type
		self.init_args = init_args

		self.inlets = [ Uninit ] * inlets
		self.outlets = [ Uninit ] * outlets
		self.status = Processor.OK 
		self.obj_id = MFPApp().remember(self)

		# gui params are updated by the gui slave
		self.gui_params = dict(obj_id=self.obj_id, num_inlets=inlets, num_outlets=outlets)

		# dsp_inlets and dsp_outlets are the processor inlet/outlet numbers 
		# of the ordinal inlets/outlets of the DSP object. 
		# for example dsp_outlets = [2] means processor outlet 2 
		# corresponds to outlet 0 of the underlying DSP object 
		self.dsp_obj = None 
		self.dsp_inlets = []
		self.dsp_outlets = [] 

		self.connections_out = [[] for r in range(outlets)]
		self.connections_in = [[] for r in range(inlets)]

	def dsp_init(self, proc_name, **params):
		self.dsp_obj = DSPObject(self.obj_id, proc_name, len(self.dsp_inlets),
						         len(self.dsp_outlets), params)
		self.gui_params['dsp_inlets'] = self.dsp_inlets
		self.gui_params['dsp_outlets'] = self.dsp_outlets

	def dsp_setparam(self, param, value):
		self.dsp_obj.setparam(param, value)

	def dsp_getparam(self, param, value):
		return self.dsp_obj.getparam(param, value)

	def delete(self):
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
			self.dsp_obj.delete()

	def parse_obj(self, argstring):
		if argstring == '' or argstring is None:
			return ()

		# FIXME: evaluator defines context, should be in patch
		e = Evaluator()
		return e.eval(argstring)

	def parse_args(self, argstring):
		if argstring == '' or argstring is None:
			return ((), {})

		# FIXME: evaluator defines context, should be in patch
		e = Evaluator()
		return e.eval_arglist(argstring)

	def resize(self, inlets, outlets):
		if inlets > len(self.inlets):
			newin = inlets - len(self.inlets)
			self.inlets += [ Uninit ] * newin
			self.connections_in += [[] for r in range(newin)]
		else:
			for inlet in range(inlets, len(self.inlets)):
				for tobj, tport in self.connections_in[inlet]:
					tobj.disconnect(tport, self, inlet)
			self.inlets[inlets:] = []

		if outlets > len(self.outlets):
			newout = outlets-len(self.outlets)
			self.outlets += [ Uninit ] * newout
			self.connections_out += [[] for r in range(newout) ]
		else:
			for outlet in range(outlets, len(self.outlets)):
				for tobj, tport in self.connections_out[outlet]:
					self.disconnect(outlet, tobj, tport)
			self.outlets[outlets:] = []
			self.connections_out[outlets:] = []

	def connect(self, outlet, target, inlet):
		# is this a DSP connection? 
		if outlet in self.dsp_outlets:
			self.dsp_obj.connect(self.dsp_outlets.index(outlet),
						         target.obj_id, target.dsp_inlets.index(inlet))

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
			self.dsp_obj.disconnect(self.dsp_outlets.index(outlet), 
						            target.obj_id, target.dsp_inlets.index(inlet))

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
			log.debug("send failed:", self, value, inlet)
			import traceback
			tb = traceback.format_exc()
			self.error(tb)

	def _send(self, value, inlet=0): 
		work = [] 
		if inlet >= 0:
			self.inlets[inlet] = value

		if inlet in self.hot_inlets or inlet == -1:
			self.outlets = [ Uninit ] * len(self.outlets)
			if inlet == -1:
				self.dsp_response(value[0], value[1])
			elif isinstance(value, MethodCall):
				self.method(value, inlet)
			else:
				self.trigger()
			for conns, val in zip(self.connections_out, self.outlets):
				if val is not Uninit:
					for target, inlet in conns:
						work.append((target, val, inlet))
		elif inlet in self.dsp_inlets:
			self.dsp_obj.setparam("_sig_" + str(inlet), float(value))

		return work 

	def method(self, message, inlet):
		'''Default method handler ignores which inlet the message was received on'''
		message.call(self)

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

