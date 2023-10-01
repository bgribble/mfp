import threading
import asyncio
from unittest import IsolatedAsyncioTestCase
from mfp.mfp_app import MFPApp
from mfp.patch import Patch
from mfp.scope import NaiveScope
from mfp import Bang, log, builtins
from mfp.processor import Processor


async def mkproc(case, init_type, init_args=None):
    return await MFPApp().create(init_type, init_args, case.patch, None, init_type)


class LimitedIncr (Processor):
    def __init__(self, patch, limit=0):
        self.limit = limit
        self.lastval = None
        Processor.__init__(self, 1, 1, 'limitedincr', '', patch, None, None)

    async def trigger(self):
        if self.inlets[0] < self.limit:
            self.outlets[0] = self.inlets[0] + 1
            self.lastval = self.outlets[0]


class FanOut (Processor):
    trail = []

    def __init__(self, patch, tag):
        self.patch = Patch('default', '', None, NaiveScope(), 'default')
        self.tag = tag
        Processor.__init__(self, 1, 4, "fanout", '', patch, None, None)

    async def trigger(self):
        self.outlets[0] = self.outlets[1] = self.outlets[2] = self.outlets[3] = Bang
        FanOut.trail.append(self.tag)


class StackDepthTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        MFPApp().no_gui = True
        MFPApp().no_dsp = True
        MFPApp().next_obj_id = 0
        MFPApp().objects = {}
        log.log_quiet = True
        log.log_thread = threading.get_ident()
        log.log_loop = asyncio.get_event_loop()
        await MFPApp().setup()
        builtins.register()
        self.patch = Patch('default', '', None, NaiveScope(), 'default')
        self.var = await mkproc(self, "var", "0")
        self.inc = LimitedIncr(self.patch)
        await self.var.connect(0, self.inc, 0)
        await self.inc.connect(0, self.var, 0)

    async def test_100(self):
        '''test_100: 100 recursions doesn't overflow stack'''
        self.inc.limit = 100
        await self.var.send(0, 0)
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 100)

    async def test_1000(self):
        '''test_1000: 1000 recursions doesn't overflow stack'''
        self.inc.limit = 1000
        await self.var.send(0, 0)
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 1000)

    async def test_10000(self):
        '''test_10000: 10000 recursions doesn't overflow stack'''
        self.inc.limit = 10000
        await self.var.send(0, 0)
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 10000)

    async def test_100000(self):
        '''test_100000: 100000 recursions doesn't overflow stack'''
        self.inc.limit = 100000
        await self.var.send(0, 0)
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 100000)


class DepthFirstTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        MFPApp().no_gui = True
        MFPApp().no_dsp = True
        MFPApp().next_obj_id = 0
        MFPApp().objects = {}
        log.log_quiet = True
        log.log_thread = threading.get_ident()
        log.log_loop = asyncio.get_event_loop()
        await MFPApp().setup()
        builtins.register()
        self.patch = Patch('default', '', None, NaiveScope(), 'default')
        FanOut.trail = []
        self.procs = [FanOut(self.patch, i) for i in range(0, 10)]
        for i in range(1, 5):
            await self.procs[0].connect(i - 1, self.procs[i], 0)
        for i in range(5, 9):
            await self.procs[1].connect(i - 5, self.procs[i], 0)
        await self.procs[3].connect(0, self.procs[9], 0)

    async def test_depthfirst(self):
        '''test_depthfirst: depth-first execution order is preserved'''
        await self.procs[0].send(Bang, 0)
        self.assertEqual(FanOut.trail, [0, 1, 5, 6, 7, 8, 2, 3, 9, 4])
