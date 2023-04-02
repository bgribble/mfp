import asyncio
import threading
import inspect


help_message = """Step debugger help

A Python REPL with debugging commands defined

Useful variables:
  app: the MFP application object
  target: The currently active processor

Debug commands:
  n, next: Perform next action
  r, run: Run free until a breakpoint
  i, info: Print summary of target object state
  h, help: This message
"""


class StepDebugger:
    def __init__(self):
        self.tasklist = []
        self.enabled = False
        self.target = None
        self.shadowed_bindings = {}
        self.event_loop_thread = threading.get_ident()
        self.event_loop = asyncio.get_event_loop()

    def set_target(self, target):
        from .mfp_app import MFPApp
        if target != self.target:
            old_target = self.target
            self.target = target
            if old_target:
                old_target.conf(debug=False)
            if target:
                target.conf(debug=True)

            evaluator = MFPApp().console.evaluator
            evaluator.local_names["target"] = self.target

    async def enable(self, target=None):
        from .mfp_app import MFPApp
        self.enabled = True

        self.set_target(target)

        evaluator = MFPApp().console.evaluator

        for b in ["next", "run", "info", "help", "n", "r", "i", "h", "target"]:
            if b in evaluator.local_names and b not in self.shadowed_bindings:
                self.shadowed_bindings[b] = evaluator.local_names[b]

        evaluator.local_names["next"] = self.mdb_next("next")
        evaluator.local_names["n"] = self.mdb_next("n")
        evaluator.local_names["run"] = self.mdb_run("run")
        evaluator.local_names["r"] = self.mdb_run("r")
        evaluator.local_names["info"] = self.mdb_info("info")
        evaluator.local_names["i"] = self.mdb_info("i")
        evaluator.local_names["help"] = self.mdb_help("help")
        evaluator.local_names["h"] = self.mdb_help("h")

    def disable(self):
        from .mfp_app import MFPApp
        self.enabled = False
        evaluator = MFPApp().console.evaluator

        for b in ["n", "r", "i", "h", "next", "run", "info", "help"]:
            if b in evaluator.local_names and inspect.isawaitable(evaluator.local_names[b]):
                evaluator.local_names[b].close()
            if b in self.shadowed_bindings:
                evaluator.local_names[b] = self.shadowed_bindings[b]
            else:
                del evaluator.local_names[b]

    def add_task(self, task, description, target):
        self.tasklist.append((task, description, target))

    async def mdb_next(self, local_name):
        from .mfp_app import MFPApp
        evaluator = MFPApp().console.evaluator
        evaluator.local_names[local_name] = self.mdb_next(local_name)
        info = await self.step_next()
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
        evaluator = MFPApp().console.evaluator
        evaluator.local_names[local_name] = self.mdb_run(local_name)
        info = await self.step_run()

    async def mdb_help(self, local_name):
        from .mfp_app import MFPApp
        evaluator = MFPApp().console.evaluator
        evaluator.local_names[local_name] = self.mdb_help(local_name)

        await MFPApp().gui_command.console_write(help_message)


    async def mdb_info(self, local_name):
        from .mfp_app import MFPApp
        evaluator = MFPApp().console.evaluator
        evaluator.local_names[local_name] = self.mdb_info(local_name)

        proc_args = f"{' ' + self.target.init_args if self.target.init_args else ''}"
        proc_descrip = f"{self.target.init_type}{proc_args}"

        await MFPApp().gui_command.console_write(
            f"Target: [{proc_descrip}] name={self.target.name}\n\n"
        )
        for ind, i in enumerate(self.target.inlets):
            await MFPApp().gui_command.console_write(
                f"   inlet {ind}: {self.target.inlets[ind]}\n"
            )

        await MFPApp().gui_command.console_write("\n")

        for ind, i in enumerate(self.target.outlets):
            await MFPApp().gui_command.console_write(
                f"   outlet {ind}: {self.target.outlets[ind]}\n"
            )

        if self.tasklist:
            next_msg = self.tasklist[0][1]
            await MFPApp().gui_command.console_write(
                f"next: {next_msg}\n"
            )

    async def show_prompt(self):
        from .mfp_app import MFPApp
        new_prompt = "mdb> "
        await MFPApp().gui_command.console_set_prompt(new_prompt)
        await MFPApp().gui_command.console_show_prompt(new_prompt)

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

        task, description, target = self.tasklist[0]
        self.tasklist[:1] = []
        self.set_target(target)
        await task
        if self.tasklist:
            task, description, target = self.tasklist[0]
            return description
        return None

    async def step_run(self):
        self.set_target(None)
        await self.show_leave()
        while self.tasklist and len(self.tasklist) > 1:
            await self.step_next()

        if len(self.tasklist):
            task, description, target = self.tasklist[0]
            self.disable()
            await task

        return None
