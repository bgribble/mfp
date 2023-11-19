#! /usr/bin/env python
'''
pyfunc.py: Wrappers for common unary and binary Python functions

Copyright (c) 2010-2017 Bill Gribble <grib@billgribble.com>
'''
import copy

from ..processor import Processor
from ..mfp_app import MFPApp
from ..method import MethodCall
from ..bang import Bang, Uninit

from mfp import log


def get_arglist(thunk):
    if hasattr(thunk, '__code__'):
        return thunk.__code__.co_varnames
    elif hasattr(thunk, '__func__'):
        return thunk.__func__.__code__.co_varnames
    else:
        return None


def isiterable(obj):
    try:
        iter(obj)
        return True
    except TypeError:
        return False


class CallFunction(Processor):
    doc_tooltip_obj = "Call a n-ary function"
    doc_tooltip_inlet = ["Callable to set and call or Bang to call"]
    doc_tooltip_outlet = ["Call result"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        self.arity = 0
        self.thunk = lambda: None

        if len(initargs):
            self.arity = initargs[0]
            self.resize(self.arity + 1, 1)

    async def trigger(self):
        if self.inlets[0] is not Bang:
            self.thunk = self.inlets[0]

        self.outlets[0] = self.thunk(*self.inlets[1:])


class ApplyMethod(Processor):
    doc_tooltip_obj = "Create a method call object"
    doc_tooltip_inlet = ["Name of method",
                         "Positional arguments to method call",
                         "Keyword arguments to method call"]

    doc_tooltip_outlet = ["MethodCall object output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.method_name = None
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.method_name = str(initargs[0])

    async def trigger(self):
        pargs = None
        kargs = None

        if self.inlets[0] is not Bang:
            self.method_name = str(self.inlets[0])

        if self.inlets[1] is not Uninit:
            pargs = self.inlets[1]

        if self.inlets[2] is not Uninit:
            kargs = self.inlets[2]

        if kargs is not None and pargs is not None:
            self.outlets[0] = MethodCall(self.method_name, *pargs, **kargs)
        elif pargs is not None:
            self.outlets[0] = MethodCall(self.method_name, *pargs)
        elif kargs is not None:
            self.outlets[0] = MethodCall(self.method_name, **kargs)
        else:
            self.outlets[0] = MethodCall(self.method_name)


class GetElement(Processor):
    doc_tooltip_obj = "Get element or attribute from object"
    doc_tooltip_inlet = ["Object to get from",
                         "Element to get (default: initarg 0)"]
    doc_tooltip_outlet = ["Specified element output", "Passthru of source"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        self.default_element = None
        if "default" in kwargs:
            self.default_element = kwargs["default"]

        self.elements = None
        if len(initargs):
            self.elements = initargs

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.elements = self.inlets[1]
            if not isinstance(self.inlets[1], (list, tuple)):
                elt = self.inlets[1]
                if isinstance(elt, str) or not isiterable(elt):
                    self.elements = [elt]
                else:
                    self.elements = list(elt)

        if self.elements is None:
            return

        values = []

        for element in self.elements:
            if isinstance(self.inlets[0], (list, tuple, str)):
                idx = int(element)
                if idx < len(self.inlets[0]):
                    values.append(self.inlets[0][int(element)])
                else:
                    if callable(self.default_element):
                        default = self.default_element()
                    else:
                        default = self.default_element
                    values.append(default)
            elif isinstance(self.inlets[0], dict):
                if element in self.inlets[0]:
                    values.append(self.inlets[0].get(element))
                else:
                    if callable(self.default_element):
                        default = self.default_element()
                    else:
                        default = self.default_element
                    values.append(default)
            else:
                if hasattr(self.inlets[0], element):
                    values.append(getattr(self.inlets[0], element))
                else:
                    if callable(self.default_element):
                        default = self.default_element()
                    else:
                        default = self.default_element
                    values.append(default)

        if len(values) == 1:
            self.outlets[0] = values[0]
        else:
            self.outlets[0] = values

        self.outlets[1] = self.inlets[0]


class SetElement(Processor):
    doc_tooltip_obj = "Set element or attribute of object"
    doc_tooltip_inlet = ["Object to modify",
                         "Element to set (default: initarg 0)",
                         "Value to set (default: initarg 1)"]
    doc_tooltip_outlet = ["Modified object"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)
        initargs, _ = self.parse_args(init_args)
        self.element = None
        self.newval = None

        if len(initargs) > 1:
            self.newval = initargs[1]

        if len(initargs):
            self.element = initargs[0]

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            element = self.inlets[1]
        else:
            element = self.element

        if self.inlets[2] is not Uninit:
            newval = self.inlets[2]
        else:
            newval = self.newval

        target = copy.copy(self.inlets[0])

        if element is None:
            return

        if isinstance(target, str):
            element = int(element)
            str_items = list(target)
            str_items[element] = newval
            target = ''.join(str_items)
        elif isinstance(element, (int, float)) or isinstance(target, dict):
            target[element] = newval
        elif isinstance(element, str):
            setattr(target, element, newval)

        self.outlets[0] = target


class GetSlice(Processor):
    doc_tooltip_obj = "Get a slice of list elements"
    doc_tooltip_inlet = ["Object to get from",
                         "Start of slice (default: initarg 0)",
                         "End of slice (default: end of input or initarg 1)",
                         "Stride (default: 1 or initarg 2)"
                         ]
    doc_tooltip_outlet = ["Slice output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 4, 1, init_type, init_args, patch, scope, name)
        initargs, _ = self.parse_args(init_args)
        self.slice_end = None
        self.slice_start = 0
        self.stride = 1

        if len(initargs) > 2:
            self.stride = initargs[2]
        if len(initargs) > 1:
            self.slice_end = initargs[1]
        if len(initargs):
            self.slice_start = initargs[0]

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.slice_start = self.inlets[1]

        if self.inlets[2] is not Uninit:
            self.slice_end = self.inlets[2]

        if self.inlets[3] is not Uninit:
            self.stride = self.inlets[3]

        if self.slice_end is not None:
            self.outlets[0] = self.inlets[0][
                self.slice_start:self.slice_end:self.stride
            ]
        else:
            self.outlets[0] = self.inlets[0][self.slice_start::self.stride]


class PyEval(Processor):
    doc_tooltip_obj = "Evaluate Python expression"
    doc_tooltip_inlet = ["Expression to evaluate"]
    doc_tooltip_outlet = ["Result of evaluation"]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.bindings = {}

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        if len(initargs):
            self.bindings = initargs[0]

    async def trigger(self):
        if isinstance(self.inlets[0], MethodCall):
            self.inlets[0].call(self)
        else:
            self.outlets[0] = self.patch.parse_obj(self.inlets[0], **self.bindings)

    def clear(self):
        self.bindings = {}

    def bind(self, **kwargs):
        for name, value in kwargs.items():
            self.bindings[name] = value

class PyFunc(Processor):
    doc_tooltip_obj = "Evaluate function"

    def __init__(self, init_type, init_args, patch, scope, name):
        if init_args:
            thunktxt = "lambda " + init_args
        else:
            thunktxt = "lambda: None"

        self.thunk = patch.parse_obj(thunktxt)

        arguments = get_arglist(self.thunk)

        if arguments is not None:
            self.argcount = len(arguments)
            self.doc_tooltip_inlet = []
            for v in arguments:
                self.doc_tooltip_inlet.append("Argument %s" % v)
        else:
            self.argcount = None
            self.doc_tooltip_inlet = ["List or tuple of arguments"]

        Processor.__init__(self, self.argcount or 1, 1, init_type, init_args, patch, scope, name)

    async def trigger(self):
        if isinstance(self.inlets[0], MethodCall):
            self.inlets[0].call(self)
        elif self.argcount:
            self.outlets[0] = self.thunk(*self.inlets[:self.argcount])
        else:
            self.outlets[0] = self.thunk(self.inlets[0])


class PyAutoWrap(Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        self.thunk = patch.parse_obj(init_type)
        self.argcount = 0
        initargs, kwargs = patch.parse_args(init_args)

        arguments = get_arglist(self.thunk)

        if arguments is not None:
            self.argcount = len(arguments)
            if hasattr(self.thunk, '__doc__') and self.thunk.__doc__ is not None:
                self.doc_tooltip_obj = self.thunk.__doc__.split("\n")[0]
            self.doc_tooltip_inlet = []
            for v in arguments:
                self.doc_tooltip_inlet.append("Argument %s" % v)
        else:
            self.argcount = 0
            self.doc_tooltip_inlet = ["List or tuple of arguments"]

        Processor.__init__(self, max(1, self.argcount), 1, init_type, init_args, patch, scope, name)

        for index, arg in enumerate(initargs):
            if index < len(self.inlets):
                self.inlets[index+1] = arg

    async def trigger(self):
        if isinstance(self.inlets[0], MethodCall):
            self.inlets[0].call(self)
        elif self.argcount:
            args = [ x for x in self.inlets[:self.argcount] if x is not Uninit]
            self.outlets[0] = self.thunk(*args)
        else:
            arg = self.inlets[0]
            self.outlets[0] = self.thunk(arg)

class PyCompareRoute(Processor):
    """
    PyCompareRoute -- route input to output selected by comparison

    [>: 0] routes inlet 1 to outlet 1 if greater than 0, else outlet 2
    """

    doc_tooltip_inlet = ["Argument 1", "Argument 2 (default: initarg 0)"]

    def __init__(self, pyfunc, init_type, init_args, patch, scope, name):
        self.function = pyfunc
        Processor.__init__(self, 2, 2, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if self.function.__doc__:
            self.doc_tooltip_obj = self.function.__doc__.split("\n")[0]

        if len(initargs) == 1:
            self.inlets[1] = initargs[0]

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            cmpval = bool(self.function(self.inlets[0], self.inlets[1]))
        else:
            # hope for a default
            cmpval = bool(self.function(self.inlets[0]))
        if cmpval:
            self.outlets[0] = self.inlets[0]
        else:
            self.outlets[1] = self.inlets[0]


class PyBinary(Processor):
    doc_tooltip_inlet = ["Argument 1", "Argument 2 (default: initarg 0)"]

    def __init__(self, pyfunc, init_type, init_args, patch, scope, name):
        self.function = pyfunc
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if self.function.__doc__:
            self.doc_tooltip_obj = self.function.__doc__.split("\n")[0]

        if len(initargs) == 1:
            self.inlets[1] = initargs[0]

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.outlets[0] = self.function(self.inlets[0], self.inlets[1])
        else:
            # hope for a default
            self.outlets[0] = self.function(self.inlets[0])

class PyUnary(Processor):
    doc_tooltip_inlet = ["Argument"]

    def __init__(self, pyfunc, init_type, init_args, patch, scope, name):
        self.function = pyfunc
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        if self.function.__doc__:
            self.doc_tooltip_obj = self.function.__doc__.split("\n")[0]

    async def trigger(self):
        self.outlets[0] = self.function(self.inlets[0])

class PyNullary(Processor):
    def __init__(self, pyfunc, init_type, init_args, patch, scope, name):
        self.function = pyfunc
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        if self.function.__doc__:
            self.doc_tooltip_obj = self.function.__doc__.split("\n")[0]

    async def trigger(self):
        self.outlets[0] = self.function()


def mk_nullary(pyfunc, name, doc=None):
    def factory(iname, args, patch, scope, obj_name):
        proc = PyNullary(pyfunc, iname, args, patch, scope, obj_name)
        if doc:
            proc.doc_tooltip_obj = doc
        return proc
    MFPApp().register(name, factory)

def mk_binary(pyfunc, name, doc=None):
    def factory(iname, args, patch, scope, obj_name):
        proc = PyBinary(pyfunc, iname, args, patch, scope, obj_name)
        if doc:
            proc.doc_tooltip_obj = doc
        return proc
    MFPApp().register(name, factory)


def mk_unary(pyfunc, name, doc=None):
    def factory(iname, args, patch, scope, obj_name):
        proc = PyUnary(pyfunc, iname, args, patch, scope, obj_name)
        if doc:
            proc.doc_tooltip_obj = doc
        return proc
    MFPApp().register(name, factory)


def mk_cmproute(pyfunc, name, doc=None):
    def factory(iname, args, patch, scope, obj_name):
        proc = PyCompareRoute(pyfunc, iname, args, patch, scope, obj_name)
        if doc:
            proc.doc_tooltip_obj = doc
        return proc
    MFPApp().register(name, factory)


import operator
import math
import cmath

def make_date(args):
    import datetime

    if isinstance(args, datetime.datetime):
        return args.date()
    else:
        return datetime.date(*args)

def applyargs(func):
    def wrapped(args):
        return func(*args)
    return wrapped

def register():
    MFPApp().register("get", GetElement)
    MFPApp().register("set!", SetElement)
    MFPApp().register("slice", GetSlice)
    MFPApp().register("eval", PyEval)
    MFPApp().register("apply", ApplyMethod)
    MFPApp().register("call", CallFunction)

    MFPApp().register("func", PyFunc)

    mk_unary(lambda l: l[0], "first")
    mk_unary(lambda l: l[1:], "rest")
    mk_unary(lambda l: list(sorted(l)), "sort")

    mk_binary(operator.add, "+", "Add")
    mk_binary(operator.sub, "-", "Subtract")
    mk_binary(operator.mul, "*", "Multiply")
    mk_binary(operator.truediv, "/", "Divide")
    mk_binary(operator.ifloordiv, "//", "Integer divide")
    mk_binary(operator.mod, "%", "Modulo")
    mk_binary(operator.pow, "^", "Raise to a power")
    mk_binary(operator.pow, "**", "Raise to a power")

    mk_binary(math.log, "log")
    mk_unary(math.exp, "exp")
    mk_unary(math.log10, "log10")
    mk_binary(math.pow, "pow")

    mk_unary(math.sin, "sin")
    mk_unary(math.cos, "cos")
    mk_unary(math.tan, "tan")
    mk_unary(math.acos, "acos")
    mk_unary(math.asin, "asin")
    mk_binary(math.atan2, "atan2")

    mk_binary(operator.gt, ">", "Greater-than comparison")
    mk_binary(operator.lt, "<", "Less-than comparison")
    mk_binary(operator.ge, ">=", "Greater than or equal comparison")
    mk_binary(operator.le, "<=", "Less than or equal comparison")
    mk_binary(operator.eq, "==", "Equality comparison")
    mk_binary(operator.ne, "!=", "Not-equal comparison")

    mk_cmproute(operator.gt, ">:", "Route on greater-than comparison")
    mk_cmproute(operator.lt, "<:", "Route on less-than comparison")
    mk_cmproute(operator.ge, ">=:", "Route on greater than or equal comparison")
    mk_cmproute(operator.le, "<=:", "Route on less than or equal comparison")
    mk_cmproute(operator.eq, "==:", "Route on equality comparison")
    mk_cmproute(operator.ne, "!=:", "Route on not-equal comparison")

    mk_binary(max, "max", "Maximum of 2 inputs")
    mk_binary(min, "min", "Minimum of 2 inputs")

    mk_unary(abs, "abs", "Absolute value/magnitude")
    mk_unary(operator.neg, "neg", "Negate value")
    mk_unary(cmath.phase, "phase", "Angle (radians) of complex number")

    # logical/bit ops
    mk_unary(operator.not_, "not", "Logical negate")
    mk_binary(operator.and_, "and", "Logical and")
    mk_binary(operator.or_, "or", "Logical or")
    mk_binary(operator.xor, "xor", "Logical xor")
    mk_binary(operator.lshift, "<<", "Bit-shift left")
    mk_binary(operator.rshift, ">>", "Bit-shift right")

    # type converters
    mk_binary(complex, "complex", "Convert to complex")
    mk_unary(int, "int", "Convert to integer")
    mk_unary(float, "float", "Convert to float")
    mk_unary(tuple, "tuple", "Convert to tuple")
    mk_unary(list, "list", "Convert to list")
    mk_unary(type, "type", "Extract object type")
    mk_unary(dict, "dict", "Convert to dictionary")
    mk_unary(set, "set", "Convert to set")

    # string methods
    mk_unary(
        lambda s: s.strip() if isinstance(s, str) else s,
        "strip", "Strip whitespace and newlines")

    mk_binary(
        lambda instr, splitstr=" ": instr.split(splitstr) if isinstance(instr, str) else instr,
        "split", "Split a string into pieces")

    mk_binary(
        lambda inval, joinstr="": joinstr.join(inval) if isiterable(inval) else inval,
        "join", "Concatenate an array or tuple of strings into one")

    mk_binary(
        lambda instr, initial: instr.startswith(initial) if isinstance(instr, str) else False,
        "startswith", "Test if string starts with another string")

    mk_cmproute(
        lambda instr, initial: instr.startswith(initial) if isinstance(instr, str) else False,
        "startswith:", "Route on whether string starts with another string")

    from datetime import datetime
    mk_nullary(datetime.now, "now", "Current time-of-day")
    mk_unary(applyargs(datetime), "datetime", "Create a datetime object")
    mk_unary(make_date, "date", "Convert to a date")
