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

    async def runsource(self, source, filename="<MFP interactive console>", symbol="single"):
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
            return InterpreterResponse(continued=False, value=None)

        output = []
        results = []
        try:
            stree = ast.parse(source)
            for obj in stree.body:
                if isinstance(obj, ast.Expr):
                    results.append(
                        # in the interactive console, 'print' should return its
                        # args as a string since stdout is useless
                        #
                        # FIXME do something about input
                        await self.evaluator.eval_async(
                            source,
                            **{"print": lambda *args: ' '.join([str(a) for a in args])}
                        )
                    )
                else:
                    self.evaluator.exec_str(source)
            for r in results:
                output.append(repr(r))
        except SystemExit:
            raise
        except Exception:
            self.showtraceback()

        if results == [None]:
            resp_output = None
        else:
            resp_output = "\n".join(output)
        return InterpreterResponse(continued=False, value=resp_output)
