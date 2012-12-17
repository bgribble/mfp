from mfp.main import MFPApp
from mfp import builtins


def setup():
    MFPApp.no_gui = True
    builtins.register()


def teardown():
    MFPApp().finish()
