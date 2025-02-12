

# build with 'python ./setup.py install'
from setuptools import setup

setup (name = 'mfp',
       version = '0.7.2',
       description = 'Music for programmers',
       packages = [
           'mfp', 'mfp.builtins',
           'mfp.gui', 'mfp.gui.modes',
           'mfp.gui.imgui', 'mfp.gui.imgui.app_window',
           'mfp.gui.clutter', 'mfp.gui.clutter.xyplot'
       ],
       entry_points = { 'console_scripts': ['mfpmain=mfp.mfp_main:main_sync_wrapper',
                                            'mfpgui=mfp.gui_main:main_sync_wrapper'] },
       package_data = { 'mfp.gui': ['mfp.glade'] })
