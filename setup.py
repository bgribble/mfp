

# build with 'python ./setup.py install' 
from setuptools import setup

def shcall(cmdline):
    from subprocess import Popen,PIPE
    return Popen(cmdline.split(), stdout=PIPE).communicate()[0].decode()

def git_version(): 
    vers = shcall(b"git show --oneline").split('\n')[0].split(' ')[0]
    if not isinstance(vers, str):
        vers = vers.decode()
    return 'git_' + str(vers.strip())

setup (name = 'mfp',
       version = '0.06_' + git_version(),
       description = 'Music for programmers',
       packages = ['mfp', 'mfp.builtins', 'mfp.rpc', 
                   'mfp.gui', 'mfp.gui.xyplot', 'mfp.gui.modes' ],
       entry_points = { 'console_scripts': ['mfp=mfp.mfp_main:main_sync_wrapper',
                                            'mfpgui=mfp.gui_main:main'] },
       package_data = { 'mfp.gui': ['mfp.glade'] })
