#! /usr/bin/env python
'''
interpreter.py
Implement a wrapped-up InteractiveInterpreter subclass for use in
the GUI or text-mode console
'''

import ast
import io
from code import InteractiveInterpreter
from contextlib import redirect_stdout, redirect_stderr
from carp.serializer import Serializable
from .evaluator import Evaluator


class InterpreterResponse (Serializable):
    def __init__(self, **kwargs):
        self.continued = False
        self.value = None
        self.stdout = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self):
        return dict(
            continued=self.continued,
            value=self.value,
            stdout=self.stdout
        )


class Interpreter (InteractiveInterpreter):
    def __init__(self, local):
        self.evaluator = Evaluator(local_bindings=local)
        InteractiveInterpreter.__init__(self)

    async def runsource(self, source, filename="<MFP interactive console>", symbol="single"):
        # we will capture stdout with this
        f = io.StringIO()
        resp = None
        results = []

        with redirect_stdout(f):
            with redirect_stderr(f):
                code = False
                try:
                    code = self.compile(source, filename, symbol)
                except (OverflowError, SyntaxError, ValueError):
                    # Case 1
                    self.showsyntaxerror(filename)

                if code is False:
                    return InterpreterResponse(continued=False, value=None, stdout=f.getvalue())

            if code is None:
                # Case 2
                resp = InterpreterResponse(continued=True)

            if not resp and not len(source.strip()):
                resp = InterpreterResponse(continued=False, value=None)

            if not resp:
                output = []
                try:
                    stree = ast.parse(source)
                    for obj in stree.body:
                        if isinstance(obj, ast.Expr):
                            results.append(
                                # in the interactive console, 'print' should return its
                                # args as a string since stdout is useless
                                #
                                # FIXME do something about input
                                await self.evaluator.eval_async(source)
                            )
                        else:
                            self.evaluator.exec_str(source)
                    for r in results:
                        output.append(repr(r))
                except SystemExit:
                    raise
                except Exception:
                    self.showtraceback()
        if resp:
            return resp

        if results == [None]:
            resp_output = None
        else:
            resp_output = "\n".join(output)
        resp = InterpreterResponse(continued=False, value=resp_output, stdout=f.getvalue())

        return resp
