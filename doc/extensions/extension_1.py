
from mfp.processor import Processor
from mfp.main import MFPApp

class Extension1 (Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 0, init_type, init_args, patch, scope, name)
        self.dsp_inlets = [0]
        self.dsp_outlets = [0] 
        self.dsp_init("ext~")

    def trigger(self):
        pass 

MFPApp().register("ext1~", Extension1)
