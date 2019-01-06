
def register():
    from . import var
    var.register()
    from . import metro
    metro.register()
    from . import printformat
    printformat.register()
    from . import pyfunc
    pyfunc.register()
    from . import audio
    audio.register()
    from . import osc
    osc.register()
    from . import sig
    sig.register()
    from . import route
    route.register()
    from . import trigger
    trigger.register()
    from . import inletoutlet
    inletoutlet.register()
    from . import line
    line.register()
    from . import noise
    noise.register()
    from . import arith
    arith.register()
    from . import file
    file.register()
    from . import loop
    loop.register()
    from . import buffer
    buffer.register()
    from . import midi
    midi.register()
    from . import note2freq
    note2freq.register()
    from . import plot
    plot.register()
    from . import listops
    listops.register()
    from . import ampl
    ampl.register()
    from . import snap
    snap.register()
    from . import biquad
    biquad.register()
    from . import sendrcv
    sendrcv.register()
    from . import phasor
    phasor.register()
    from . import radiogroup
    radiogroup.register()
    from . import dbmath
    dbmath.register()
    from . import plugin
    plugin.register()
    from . import loadbang
    loadbang.register()
    from . import oscutils
    oscutils.register()
    from . import delay
    delay.register()
    from . import dispatch
    dispatch.register()
    from . import latency
    latency.register()
    from . import errtest
    errtest.register()
    from . import slew
    slew.register()
    from . import bitcombine
    bitcombine.register()
    from . import pulse
    pulse.register()
    from . import pulsesel
    pulsesel.register()
    from . import stepseq
    stepseq.register()
