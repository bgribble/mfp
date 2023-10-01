
from unittest import TestCase
from mfp.patch import Patch
from ..mfp_app import MFPApp
from mfp.scope import NaiveScope
from mfp import log, builtins
import threading
import asyncio
from unittest import IsolatedAsyncioTestCase

async def mkproc(testcase, init_type, init_args=None):
    return await MFPApp().create(init_type, init_args, testcase.patch, None, init_type)

class DSPErrorTests (IsolatedAsyncioTestCase):
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
        self.errtest = await mkproc(self, "errtest~")

    async def test_configerr(self):
        await self.errtest.dsp_obj.setparam("err_config", 1.0)

    async def test_processerr(self):
        await self.errtest.dsp_obj.setparam("err_process", 1.0)

    async def test_deleteerr(self):
        await self.errtest.dsp_obj.setparam("err_delete", 1.0)
        await self.errtest.delete()

    async def asyncTearDown(self):
        await MFPApp().finish()


