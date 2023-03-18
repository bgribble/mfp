
class StepDebugger:
    def __init__(self):
        self.tasklist = []
        self.enabled = False

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    async def show_prompt(self):
        from .mfp_app import MFPApp
        await MFPApp().gui_command.console_set_prompt("mdb> ")
        await MFPApp().gui_command.console_write(
            "mdb>  "
        )

    async def show_banner(self):
        from .mfp_app import MFPApp
        await MFPApp().gui_command.console_write(
            "\nStep mode started\nn=next, r=run, h=help\n"
        )

    async def show_leave(self):
        from .mfp_app import MFPApp
        await MFPApp().gui_command.console_write(
            "Free-running mode resumed\n"
        )
        await MFPApp().gui_command.console_set_prompt(">>> ")
        await MFPApp().gui_command.console_write(
            ">>> "
        )

    async def flush(self):
        for t in self.tasklist:
            t.cancel()

    async def step_next(self):
        if not len(self.tasklist):
            return

        next_task = self.tasklist[0]
        self.tasklist[:1] = []
        await next_task

    async def step_run(self):
        self.step_execute = False
        while (not self.enabled) and self.tasklist:
            await self.step_next()
