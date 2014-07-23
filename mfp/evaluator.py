#! /usr/bin/env python2.6
'''
evaluator.py:  Augmented Python eval for strings in user interface

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

import tokenize
from StringIO import StringIO

class LazyExpr(object): 
    def __init__(self, thunk):
        self.thunk = thunk 

    def call(self): 
        return self.thunk() 

class Evaluator (object):
    global_names = {}

    def __init__(self):
        self.local_names = {'self': self}

    @classmethod
    def bind_global(self, name, obj):
        self.global_names[name] = obj

    def bind_local(self, name, obj):
        self.local_names[name] = obj

    def eval_arglist(self, evalstr):
        return self.eval(evalstr, True)

    def eval(self, evalstr, collect=False):
        def _eval_collect_args(*args, **kwargs):
            return (args, kwargs)

        str2eval = evalstr.strip()
        if not len(str2eval):
            return None

        # lazy evaluation special form 
        #   ,expression 
        # rewrites to: 
        #   LazyEval(lambda: expression)
        # this expression will be evaluated the first time the LazyExpr is 
        # passed from one object to another. 
        # 
        # this can be nested (i.e. ,,,expr is a "3 times lazy" expression that 
        # will go off after 3 links)
        
        def lazyrecurse(evalstr): 
            return (("LazyExpr(lambda: %s)" % lazyrecurse(evalstr[1:])) 
                    if evalstr[0] == ',' else evalstr)
        str2eval = lazyrecurse(str2eval) 

        sio = StringIO(str2eval)

        tokens = [t for t in tokenize.generate_tokens(sio.read)
                  if t[1] != '']

        # Method call special form:
        #   @method(arg1, arg2, ..., kwarg=val, kwarg2=val)
        # rewrites to:
        #	MethodCall("method", arg1, arg2, ... kwarg=val, kwarg2=val
        #
        # @foo is a synonym for @foo()
        if tokens[0][1] == '@' and len(tokens) >= 2:
            methname = tokens[1][1]
            if len(tokens) == 2:
                str2eval = ''.join(["MethodCall(", '"', methname, '"', ')'])
            else:
                if tokens[2][1] != '(':
                    raise SyntaxError()
                str2eval = ''.join(["MethodCall(", '"', methname, '",']
                                   + [t[1] for t in tokens[3:]])

        # setparam special form:
        #   foo='bar', bax='baz'
        # rewrites to
        #   dict(foo='bar', bax='baz')
        if len(tokens) > 2 and tokens[1][1] == '=':
            str2eval = ''.join(["dict("] + [t[1] for t in tokens] + [')'])

        # FIXME race
        if collect:
            str2eval = "_eval_collect_args(%s)" % str2eval
            self.local_names['_eval_collect_args'] = _eval_collect_args

        environ = { name: val 
                    for name, val in self.global_names.items() + self.local_names.items()
                  } 

        rv = eval(str2eval, environ)

        if collect:
            del self.local_names['_eval_collect_args']

        return rv

    def exec_str(self, pystr):
        exec(pystr, self.global_names)

    def exec_file(self, filename):
        import os.path 
        self.local_names["__file__"] = filename 
        self.local_names["__name__"] = os.path.basename(filename) 
        fileobj = open(filename, "r")
        if fileobj:
            exec(fileobj, self.global_names)


