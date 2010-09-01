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
		self.objects = []

	def load_file(self, filename):
		jsdata = open(filename, 'r').read()
		f = json.loads(jsdata)
		self.name = f.get('name')
		
		# clear old objects
		for o in self.objects:
			o.delete()

		# create new objects
		idmap = {}
		for oid, prms in f.get('objects', {})().items():
			newobj = MFPApp().create(prms.get('type'), prms.get('initargs'))
			MFPApp().configure_gui(obj, prms)
			idmap[oid] = newid

	def save_file(self, filename=None):
		f = {}
		f['name'] = self.name
		allobj = {}
		for o in self.objects:
			oinfo = o.save()
			allobj[o.obj_id] = oinfo

		f['objects'] = allobj
		savefile = open(filename, "w")
		savefile.write(json.dumps(f))		

	def add(self, obj):
		self.objects.append(obj)

