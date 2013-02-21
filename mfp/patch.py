#! /usr/bin/env python2.6
'''
patch.py
Patch class and methods 

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import os

from .processor import Processor
from .evaluator import Evaluator
from .scope import LexicalScope
from .bang import Uninit

from mfp import log


class Patch(Processor):
    display_type = "patch"

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)

        self.objects = {}
        self.scopes = {'__patch__': LexicalScope()}
        self.default_scope = self.scopes['__patch__']

        self.evaluator = Evaluator()

        self.inlet_objects = []
        self.outlet_objects = []
        self.dispatch_objects = [] 

        self.evaluator.bind_local("self", self)
        self.default_scope.bind("self", self)

        initargs, kwargs = self.parse_args(init_args)
        self.gui_params['layers'] = []

    #############################
    # name management
    #############################
    def bind(self, name, scope, obj):
        return scope.bind(name, obj)

    def unbind(self, name, scope):
        exists, val = scope.query(name)
        if exists:
            scope.unbind(name)

    def resolve(self, name, scope=None):
        if scope is not None and scope in self.scopes:
            s = self.scopes.get(scope)
            exists, val = s.query(name)
            if exists:
                return val
        elif name in self.scopes:
            return self.scopes.get(name)

        exists, val = self.default_scope.query(name)
        if exists:
            return val

        return None

    def add_scope(self, name):
        self.scopes[name] = LexicalScope()
        return self.scopes[name]

    def del_scope(self, name):
        del self.scopes[name]

    #############################
    # evaluator
    #############################

    def parse_obj(self, argstring):
        '''
        Parse and evaluate a Python expression
        '''
        if argstring == '' or argstring is None:
            return None

        return self.evaluator.eval(argstring)

    def parse_args(self, argstring):
        '''
        Parse and evaluate a Python expression representing
        a function/method argument list (returns tuple of positional
        args followed by dictionary of keyword args)

        This uses a tacky trick to capture args and kwargs which
        will generate some odd backtraces on error
        '''

        if argstring == '' or argstring is None:
            return ((), {})

        return self.evaluator.eval_arglist(argstring)

    #############################
    # patch contents management
    #############################
    def trigger(self):
        inlist = range(len(self.inlets))
        inlist.reverse()

        for i in inlist:
            if self.inlets[i] is not Uninit:
                self.inlet_objects[i].send(self.inlets[i])
                self.inlets[i] = Uninit

        for o in range(len(self.outlets)):
            self.outlets[i] = self.outlet_objects[i].outlets[0]

    def method(self, message, inlet=0):
        if len(self.dispatch_objects): 
            for d in self.dispatch_objects:
                d.send(message)
        else:
            self.baseclass_method(message, inlet)

    def baseclass_method(self, message, inlet=0):
        Processor.method(self, message, inlet) 

    def send(self, value, inlet=0):
        self.inlet_objects[inlet].send(value)

    def add(self, obj):
        if self.objects.has_key(obj.obj_id):
            return 

        self.objects[obj.obj_id] = obj
        if obj.init_type == 'inlet':
            num = obj.inletnum
            if num >= len(self.inlet_objects):
                self.inlet_objects.extend([None] * (num - len(self.inlet_objects) + 1))
            self.inlet_objects[num] = obj
            self.resize(len(self.inlet_objects), len(self.outlet_objects))

        elif obj.init_type == 'outlet':
            num = obj.outletnum
            if num >= len(self.outlet_objects):
                self.outlet_objects.extend([None] * (num - len(self.outlet_objects) + 1))
            self.outlet_objects[num] = obj
            self.resize(len(self.inlet_objects), len(self.outlet_objects))

        elif obj.init_type == 'dispatch':
            self.dispatch_objects.append(obj)

    def remove(self, obj):
        try:
            if obj.scope is not None and obj.name is not None:
                self.unbind(obj.name, obj.scope)
            del self.objects[obj.obj_id]
        except KeyError: 
            print "Error deleting obj", obj, "can't find key", obj.obj_id
            import traceback
            traceback.print_exc()

        try:
            self.inlet_objects.remove(obj)
        except ValueError:
            pass

        try:
            self.outlet_objects.remove(obj)
        except ValueError:
            pass

        try:
            self.dispatch_objects.remove(obj)
        except ValueError:
            pass



    ############################
    # load/save
    ############################

    @classmethod
    def register_file(klass, filename):
        from main import MFPApp

        def factory(init_type, init_args, patch, scope, name):
            p = Patch(init_type, init_args, patch, scope, name)
            p._load_file(filename)
            p.init_type = init_type
            return p

        basefile = os.path.basename(filename)
        parts = os.path.splitext(basefile)
        
        log.debug("Patch.register_file: registering type '%s' from file '%s'"
                  % (parts[0], filename))
        MFPApp().register(parts[0], factory)
        return (parts[0], factory)

    def _load_file(self, filename):
        from .main import MFPApp
        from .utils import splitpath 

        searchpath = MFPApp().searchpath or ""
        searchdirs = splitpath(searchpath)
        jsdata = None 

        for d in searchdirs:
            path = os.path.join(d, filename)
            try: 
                os.stat(path)
                jsdata = open(path, 'r').read()
            except OSError:
                pass 
        
        if jsdata is not None:
            self.json_deserialize(jsdata)
            for obj_id, obj in self.objects.items():
                if obj.do_onload:
                    obj.onload()

    def create_gui(self):
        from main import MFPApp
        if MFPApp().no_gui:
            return False

        # create the basic element info 
        Processor.create_gui(self)

        # for patches that are not top-level, that's all.
        if not self.gui_params.get("top_level"):
            return 

        MFPApp().gui_command.load_start()

        for oid, obj in self.objects.items():
            obj.create_gui()

        for oid, obj in self.objects.items():
            for srcport, connections in enumerate(obj.connections_out):
                for dstobj, dstport in connections:
                    MFPApp().gui_command.connect(obj.obj_id, srcport, dstobj.obj_id, dstport)
        MFPApp().gui_command.load_complete()

    def save_file(self, filename=None):
        savefile = open(filename, "w")
        savefile.write(self.json_serialize())

    def delete(self):
        print "Patch.delete()"
        for oid, obj in self.objects.items():
            print "    Deleting patch object", oid, obj
            obj.delete()
        Processor.delete(self)


# load extension methods
import patch_json
