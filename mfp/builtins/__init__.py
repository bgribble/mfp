
builtin_modules = [
    "var", "metro", "printformat", "pyfunc", "audio", "osc",
    "sig", "route", "trigger", "inletoutlet", "line", "noise",
    "arith", "file", "loop", "buffer", "midi", "note2freq",
    "plot", "listops", "ampl", "snap", "biquad", "sendrcv",
    "phasor", "radiogroup", "dbmath", "plugin", "loadbang",
    "oscutils", "delay", "dispatch", "latency", "errtest",
    "slew", "bitcombine", "pulse", "pulsesel", "stepseq",
    "vcq12", "vcfreq", "hold", "replay", "breakpoint", "faust",
    "messagerec", "quantize"
]

def register():
    import importlib
    for mod_name in builtin_modules:
        mod = importlib.import_module("." + mod_name, "mfp.builtins")
        mod.register()
