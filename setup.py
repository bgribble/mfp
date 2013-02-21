

# build with 'python ./setup.py install' 
from setuptools import setup, Extension

def shcall(cmdline):
    from subprocess import Popen,PIPE
    return Popen(cmdline.split(), stdout=PIPE).communicate()[0]

def pkgconf_cflags(pkg):
    return [ f.strip() for f in shcall("pkg-config --cflags %s" % pkg).split('-I')
             if f ]
    
def pkgconf_libs(pkg):
    return [ f.strip() for f in shcall("pkg-config --libs %s" % pkg).split('-l')
             if f ]
    
def git_version(): 
    vers = shcall("git show --oneline").split('\n')[0].split(' ')[0]
    return 'git_' + vers.strip()


x86_args = ['-march=686', '-mstackrealign', '-mpreferred-stack-boundary=4']
platform_args = [ "-DMFP_USE_SSE"]

mfp_c_sources = [
    'mfp_pyglue.c', 'mfp_jack.c', 'mfp_dsp.c', 'mfp_proc.c', 'mfp_block.c',
    'cspline.c', 'builtin_osc.c', 'builtin_adc_dac.c', 'builtin_sig.c', 'builtin_arith.c',
    'builtin_line.c', 'builtin_noise.c', 'builtin_buffer.c', 'builtin_ampl.c',
    'builtin_snap.c', 'builtin_biquad.c', 'builtin_phasor.c',
    'builtin_ladspa.c', 'builtin_delay.c',
    'test_builtins.c', 'test_block.c', 'test_schedule.c', 'test_cspline.c'
]

mfpdsp = Extension('mfpdsp',
                   libraries = ['jack', 'rt'] + pkgconf_libs("glib-2.0"),
                   extra_compile_args = platform_args + [ '-g' ],
                   include_dirs = pkgconf_cflags("glib-2.0"),
                   sources = [ 'mfpdsp/' + f for f in mfp_c_sources ]
                  )



setup (name = 'mfp',
       version = '0.01_' + git_version(),
       description = 'Music for programmers',
       packages = ['mfp', 'mfp.builtins', 'mfp.gui', 'mfp.gui.xyplot', 'mfp.gui.modes' ],
       entry_points = { 'console_scripts': [ 'mfp=mfp.main:main'] },
       package_data = { 'mfp.gui': ['mfp.glade'] },
       ext_modules = [ mfpdsp ])

