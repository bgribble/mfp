import asyncio
import threading
import inspect

from . import log


class StepDebugger:
    def __init__(self):
        self.tasklist = []
        self.enabled = False
        self.shadowed_bindings = {}
        self.event_loop_thread = threading.get_ident()
        self.event_loop = asyncio.get_event_loop()

    async def enable(self):
        from .mfp_app import MFPApp
        self.enabled = True
        evaluator = MFPApp().console.evaluator

        for b in ["next", "run", "n", "r", "info", "help"]:
            if b in evaluator.local_names and b not in self.shadowed_bindings:
                self.shadowed_bindings[b] = evaluator.local_names[b]

        evaluator.local_names["next"] = self.mdb_next("next")
        evaluator.local_names["n"] = self.mdb_next("n")
        evaluator.local_names["run"] = self.mdb_run("run")
        evaluator.local_names["r"] = self.mdb_run("r")

    def disable(self):
        from .mfp_app import MFPApp
        self.enabled = False
        evaluator = MFPApp().console.evaluator

        for b in ["next", "run", "info", "help"]:
            if b in self.shadowed_bindings:
                if b in evaluator.local_names and inspect.isawaitable(evaluator.local_names[b]):
                    evaluator.local_names[b].cancel()
                evaluator.local_names[b] = self.shadowed_bindings[b]

    def add_task(self, task, description):
        self.tasklist.append((task, description))

    async def mdb_next(self, local_name):
        from .mfp_app import MFPApp
        info = await self.step_next()
        evaluator = MFPApp().console.evaluator
        evaluator.local_names[local_name] = self.mdb_next(local_name)
        if info:
            await MFPApp().gui_command.console_write(
                f"next: {info}\n"
            )
        else:
            await MFPApp().gui_command.console_write(
                "All events processed\n"
            )

    async def mdb_run(self, local_name):
        from .mfp_app import MFPApp
        info = await self.step_run()
        evaluator = MFPApp().console.evaluator
        evaluator.local_names[local_name] = self.mdb_run(local_name)

    async def show_prompt(self):
        from .mfp_app import MFPApp
        await MFPApp().gui_command.console_set_prompt("mdb> ")
        await MFPApp().gui_command.console_write(
            "mdb> "
        )

    async def show_banner(self, message=None):
        from .mfp_app import MFPApp
        if message:
            await MFPApp().gui_command.console_write("\n" + message + "\n")

        await MFPApp().gui_command.console_write(
            "Step mode started\nn=next, r=run, h=help\n"
        )

    async def show_leave(self):
        from .mfp_app import MFPApp
        await MFPApp().gui_command.console_set_prompt(">>> ")

    async def flush(self):
        for t in self.tasklist:
            t.cancel()

    async def step_next(self):
        if not len(self.tasklist):
            return None
        task, description = self.tasklist[0]
        self.tasklist[:1] = []
        await task
        if self.tasklist:
            task, description = self.tasklist[0]
            return description
        return None

    async def step_run(self):
        await self.show_leave()
        while self.tasklist and len(self.tasklist) > 1:
            await self.step_next()
        self.enabled = False
        if len(self.tasklist):
            await self.step_next()
        return None
