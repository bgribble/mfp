#! /usr/bin/env python
'''
interpreter.py
Implement a wrapped-up InteractiveInterpreter subclass for use in
the GUI or text-mode console
'''

from carp.serializer import Serializable
from .evaluator import Evaluator
from code import InteractiveInterpreter
import ast


class InterpreterResponse (Serializable):
    def __init__(self, **kwargs):
        self.continued = False
        self.value = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return dict(
            continued=self.continued,
            value=self.value
        )

class Interpreter (InteractiveInterpreter):
    def __init__(self, local):
        self.evaluator = Evaluator(local_bindings=local)
        InteractiveInterpreter.__init__(self)

    def runsource(self, source, filename="<MFP interactive console>", symbol="single"):
        try:
            code = self.compile(source, filename, symbol)
        except (OverflowError, SyntaxError, ValueError):
            # Case 1
            self.showsyntaxerror(filename)
            return False

        if code is None:
            # Case 2
            return InterpreterResponse(continued=True)

        if not len(source.strip()):
            return InterpreterResponse(continued=False, value='')

        output = []
        try:
            results = []
            stree = ast.parse(source)
            for obj in stree.body:
                if isinstance(obj, ast.Expr):
                    results.append(self.evaluator.eval(source))
                else:
                    self.evaluator.exec_str(source)
            for r in results:
                output.append(repr(r))
        except SystemExit:
            raise
        except Exception:
            self.showtraceback()

        return InterpreterResponse(continued=False, value="\n".join(output))
