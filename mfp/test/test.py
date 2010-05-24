
import mfpdsp

mfpdsp.dsp_startup()

osc = mfpdsp.proc_create("osc~", freq=500)
dac = mfpdsp.proc_create("dac~", channel=0)

mfpdsp.proc_connect(osc, 0, dac, 0)
mfpdsp.dsp_enable()

import time 
time.sleep(10)



