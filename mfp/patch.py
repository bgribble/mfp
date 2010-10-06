#! /usr/bin/env python2.6
'''
patch.py
Patch load/save

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import simplejson as json

class Patch(object):
	def __init__(self):
		self.name = "Default"
		self.objects = {}
		self.gui_objects = {}

	def load_file(self, filename):
		jsdata = open(filename, 'r').read()
		self.load_string(jsdata)

	def load_string(self, json_data):
		from main import MFPApp

		f = json.loads(json_data)
		self.name = f.get('name')
		
		# clear old objects
		for o in self.objects.values():
			o.delete()
		self.objects = {}

		# create new objects
		idmap = {}
		idlist = f.get('objects').keys()
		idlist.sort()
		for oid in idlist:
			prms = f.get('objects')[oid]
			otype = prms.get('type')
			oargs = prms.get('initargs')
			newobj = MFPApp().create(otype, oargs)
			gp = prms.get('gui_params')
			newobj.gui_params = gp 

			if not MFPApp.no_gui:
				guiobj = MFPApp().gui_cmd.create(otype, oargs, newobj.obj_id, gp)
			else:
				guiobj = None

			idmap[int(oid)] = (newobj, guiobj)

		for oid, objects in idmap.items():
			mfpobj, guiobj = objects
			self.objects[mfpobj.obj_id] = mfpobj
			self.gui_objects[mfpobj.obj_id] = guiobj

		# make connections
		for oid, prms in f.get('objects', {}).items():
			oid = int(oid)
			conn = prms.get("connections", [])
			srcobj = idmap.get(oid)[0]
			for outlet in range(0, len(conn)):
				connlist = conn[outlet]
				for c in connlist:
					dstobj = idmap.get(c[0])[0]
					inlet = c[1]
					srcobj.connect(outlet, dstobj, inlet)
					if not MFPApp.no_gui:
						print "load_patch: connect", srcobj.obj_id, outlet, dstobj.obj_id, inlet
						MFPApp().gui_cmd.connect(srcobj.obj_id, outlet, dstobj.obj_id, inlet)

	def save_string(self):
		f = {}
		f['name'] = self.name
		allobj = {}
		for oid, o in self.objects.items():
			oinfo = o.save()
			allobj[oid] = oinfo

		f['objects'] = allobj
		return json.dumps(f)

	def save_file(self, filename=None):
		savefile = open(filename, "w")
		savefile.write(self.save_string())		

	def add(self, obj):
		self.objects[obj.obj_id] = obj



