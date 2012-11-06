#! /usr/bin/env python2.6
'''
patch.py
Patch load/save

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import simplejson as json
from .processor import Processor

def getx(o):
	return o.gui_params.get('position_x', 0)

class Patch(Processor):
	def __init__(self, init_type='none', init_args=None):
		self.objects = {}
		self.inlet_objects = []
		self.outlet_objects = []
		Processor.__init__(self, 0, 0, init_type, init_args)

	def load_file(self, filename):
		jsdata = open(filename, 'r').read()
		self.load_string(jsdata)

	def load_string(self, json_data):
		from main import MFPApp

		f = json.loads(json_data)
		self.init_type = f.get('type')
		
		# clear old objects
		for o in self.objects.values():
			o.delete()
		self.objects = {}
		self.inlet_objects = []
		self.outlet_objects = []

		# create new objects
		idmap = {}
		idlist = f.get('objects').keys()
		idlist.sort(key=lambda x: int(x))
		for oid in idlist:
			prms = f.get('objects')[oid]
			otype = prms.get('type')
			oargs = prms.get('initargs')
			newobj = MFPApp().create(otype, oargs)

			if otype == 'inlet':
				self.inlet_objects.append(newobj)
			elif otype == 'outlet':
				self.outlet_objects.append(newobj)
				newobj.patch = self

			gp = prms.get('gui_params')
			newobj.gui_params = gp 

			if not MFPApp.no_gui:
				MFPApp().gui_cmd.create(otype, oargs, newobj.obj_id, gp)

			idmap[int(oid)] = newobj

		for oid, mfpobj in idmap.items():
			self.objects[mfpobj.obj_id] = mfpobj

		# make connections
		for oid, prms in f.get('objects', {}).items():
			oid = int(oid)
			conn = prms.get("connections", [])
			srcobj = idmap.get(oid)
			for outlet in range(0, len(conn)):
				connlist = conn[outlet]
				for c in connlist:
					dstobj = idmap.get(c[0])
					inlet = c[1]
					srcobj.connect(outlet, dstobj, inlet)
					if not MFPApp.no_gui:
						MFPApp().gui_cmd.connect(srcobj.obj_id, outlet, dstobj.obj_id, inlet)
		# sort inlets and outlets by X position
		self.inlet_objects.sort(key=getx)
		self.outlet_objects.sort(key=lambda x: -getx(x))
		self.resize(len(self.inlet_objects), len(self.outlet_objects))

	def save_string(self):
		f = {}
		f['type'] = self.init_type
		allobj = {}
		keys = self.objects.keys()
		keys.sort()
		for oid in keys:
			o = self.objects.get(oid)
			oinfo = o.save()
			allobj[oid] = oinfo

		f['objects'] = allobj
		return json.dumps(f)

	def send(self, value, inlet=0):
		print self, "sending", value, "to", self.inlet_objects[inlet]
		self.inlet_objects[inlet].send(value)

	def connect(self, outlet, target, inlet):
		self.outlet_objects[outlet].connect(0, target, inlet)

	def save_file(self, filename=None):
		savefile = open(filename, "w")
		savefile.write(self.save_string())		

	def add(self, obj):
		self.objects[obj.obj_id] = obj
		if obj.init_type == 'inlet':
			self.inlet_objects.append(obj)
			self.inlet_objects.sort(key=getx)
		elif obj.init_type == 'outlet':
			self.outlet_objects.append(obj)
			self.outlet_objects.sort(key=lambda x: -getx(x))



