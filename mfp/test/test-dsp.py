import asyncio
import threading

from unittest import IsolatedAsyncioTestCase

from mfp.mfp_app import MFPApp
from mfp.patch import Patch
from mfp.scope import NaiveScope
from mfp import builtins
from mfp import log


async def mkproc(testcase, init_type, init_args=None):
    return await MFPApp().create(init_type, init_args, testcase.patch, None, init_type)


class DSPObjectTests (IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        MFPApp().no_gui = True
        MFPApp().no_restart = True
        MFPApp().next_obj_id = 0
        MFPApp().objects = {}
        log.log_quiet = True
        log.log_thread = threading.get_ident()
        log.log_loop = asyncio.get_event_loop()
        await MFPApp().setup()
        builtins.register()
        self.patch = Patch('default', '', None, NaiveScope(), 'default')

    async def test_create(self):
        '''test_create: [dsp] can make a DSP object'''
        await mkproc(self, "osc~", "500")

    async def test_read(self):
        '''test_read: [dsp] can read back a creation parameter'''
        o = await mkproc(self, "osc~", "500")
        f = await o.dsp_obj.getparam("_sig_1")
        assert f == 500

    async def test_connect_disconnect(self):
        '''test_connect_disconnect: [dsp] make/break connections'''
        inp = await mkproc(self, "in~", "0")
        outp = await mkproc(self, "out~", "0")

        await inp.connect(0, outp, 0)
        await inp.disconnect(0, outp, 0)

    async def test_delete(self):
        '''test_destroy: [dsp] destroy dsp object'''
        inp = await mkproc(self, "in~", "0")
        outp = await mkproc(self, "out~", "0")
        await inp.connect(0, outp, 0)
        await outp.delete()
        await inp.delete()

    async def asyncTearDown(self):
        await MFPApp().finish()
