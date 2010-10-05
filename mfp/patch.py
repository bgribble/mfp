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
		from main import MFPApp
		jsdata = open(filename, 'r').read()
		f = json.loads(jsdata)
		self.name = f.get('name')
		
		# clear old objects
		for o in self.objects.values():
			o.delete()
		self.objects = {}

		# create new objects
		idmap = {}
		for oid, prms in f.get('objects', {}).items():
			otype = prms.get('type')
			oargs = prms.get('initargs')
			newobj = MFPApp().create(otype, oargs)
			if not MFPApp.no_gui:
				gp = prms.get('gui_params')
				newobj.gui_params = gp 
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

	def save_file(self, filename=None):
		f = {}
		f['name'] = self.name
		allobj = {}
		for oid, o in self.objects.items():
			oinfo = o.save()
			allobj[oid] = oinfo

		f['objects'] = allobj
		savefile = open(filename, "w")
		savefile.write(json.dumps(f))		

	def add(self, obj):
		self.objects[obj.obj_id] = obj



