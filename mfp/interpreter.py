#! /usr/bin/env python
'''
interpreter.py
Implement a wrapped-up InteractiveInterpreter subclass for use in
the GUI or text-mode console
'''

from .evaluator import Evaluator
from code import InteractiveInterpreter
import ast


class Interpreter (InteractiveInterpreter):
    def __init__(self, write_cb, local):
        self.write_cb = write_cb
        self.evaluator = Evaluator()
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
            return True

        if not len(source.strip()):
            self.write('')
        else:
            try:
                results = []
                stree = ast.parse(source)
                for obj in stree.body:
                    if isinstance(obj, ast.Expr):
                        results.append(self.evaluator.eval(source))
                    else:
                        self.evaluator.exec_str(source)
                for r in results:
                    self.write(repr(r) + "\n")
            except SystemExit:
                raise
            except Exception:
                self.showtraceback()

        return False

    def write(self, msg):
        if self.write_cb:
            self.write_cb(msg)
