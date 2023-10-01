from mfp.mfp_app import MFPApp
from mfp import builtins


async def asyncSetup():
    MFPApp().no_gui = True
    builtins.register()


async def asyncTeardown():
    await MFPApp().finish()
