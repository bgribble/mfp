#! /usr/bin/env python
'''
evaluator.py:  Augmented Python eval for strings in user interface

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

import tokenize
import inspect
from io import StringIO

from mfp import log


class LazyExpr(object):
    def __init__(self, thunk):
        self.thunk = thunk

    def call(self):
        return self.thunk()


class Evaluator (object):
    global_names = {}

    def __init__(self, local_bindings=None):
        self.local_names = {}
        if local_bindings:
            self.local_names.update(**local_bindings)

    @classmethod
    def bind_global(self, name, obj):
        self.global_names[name] = obj

    def bind_local(self, name, obj):
        self.local_names[name] = obj

    def eval_arglist(self, evalstr, **extra_bindings):
        return self.eval(evalstr, True, **extra_bindings)

    async def eval_async(self, evalstr, collect=False, **extra_bindings):
        rv = self.eval(evalstr, collect=False, **extra_bindings)

        if inspect.isawaitable(rv):
            return await rv
        return rv

    def eval(self, evalstr, collect=False, **extra_bindings):
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
        # *or*
        #   @method arg1, arg2...
        # rewrites to:
        #   MethodCall("method", arg1, arg2, ... kwarg=val, kwarg2=val
        #
        # @foo is a synonym for @foo()
        if tokens[0][1] == '@' and len(tokens) >= 2:
            methname = tokens[1][1]
            if len(tokens) == 2:
                str2eval = ''.join(["MethodCall(", '"', methname, '"', ')'])
            else:
                if tokens[2][1] != '(':
                    str2eval = ''.join(
                        [
                            "MethodCall(", '"', methname, '",'
                        ]
                        + [t[1] for t in tokens[2:]] + [")"]
                    )
                else:
                    str2eval = ''.join(
                        [
                            "MethodCall(", '"', methname, '",'
                        ]
                        + [t[1] for t in tokens[3:]]
                    )

        if collect:
            str2eval = "_eval_collect_args(%s)" % str2eval
            extra_bindings['_eval_collect_args'] = _eval_collect_args
        elif len(tokens) > 2 and tokens[1][1] == '=':
            # setparam special form:
            #   foo='bar', bax='baz'
            # rewrites to
            #   dict(foo='bar', bax='baz')
            str2eval = ''.join(["dict("] + [t[1] for t in tokens] + [')'])

        environ = {
            name: val
            for name, val in (
                list(self.global_names.items()) + list(self.local_names.items())
                + list(extra_bindings.items())
            )
        }
        if "__self__" in environ:
            environ["self"] = environ["__self__"]
        if "__patch__" in environ:
            environ["patch"] = environ["__patch__"]

        rv = eval(str2eval, environ)
        return rv

    def exec_str(self, pystr, global_vars=None):
        if global_vars is not None:
            for name, value in self.global_names.items():
                if name not in global_vars:
                    global_vars[name] = value
            exec(pystr, global_vars)
        else:
            exec(pystr, self.global_names)

    def exec_file(self, filename):
        import os.path
        self.local_names["__file__"] = filename
        self.local_names["__name__"] = os.path.basename(filename)
        fileobj = open(filename, "r")
        if fileobj:
            exec(fileobj, self.global_names)
