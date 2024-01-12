"""
test-control-1 -- test basic control builtins
"""
import threading
import asyncio
from unittest import IsolatedAsyncioTestCase

from mfp.mfp_app import MFPApp
from mfp.patch import Patch
from mfp.scope import NaiveScope
from mfp.bang import Bang, Uninit
from mfp import log, builtins


async def mkproc(testcase, init_type, init_args=None):
    return await MFPApp().create(init_type, init_args, testcase.patch, None, init_type)


class PlusTest(IsolatedAsyncioTestCase):
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
        self.patch = Patch('default', '', None, NaiveScope(), 'default')
        self.plus = await mkproc(self, "+", None)
        self.out = await mkproc(self, "var")
        await self.plus.connect(0, self.out, 0)

    async def test_default(self):
        '''test with default creation args'''
        self.plus = await mkproc(self, "+", "12")
        await self.plus.connect(0, self.out, 0)
        await self.plus.send(13, 0)
        assert self.out.outlets[0] == 25

        await self.plus.send(99, 0)
        assert self.out.outlets[0] == 111

    async def test_numbers(self):
        '''test_numbers: 23 + 32 == 55'''
        await self.plus.send(23, 1)
        await self.plus.send(32, 0)
        assert self.out.outlets[0] == 55

    async def test_strings(self):
        '''test_strings: 'hello ' + 'world' == 'hello world' '''
        await self.plus.send("world", 1)
        await self.plus.send("hello ", 0)
        assert self.out.outlets[0] == "hello world"

    async def test_typeerr(self):
        '''test_typeerr: mismatched types produce nothing'''
        await self.plus.send("hello", 1)
        await self.plus.send(5, 0)

        assert self.out.outlets[0] is Uninit

    async def asyncTearDown(self):
        await MFPApp().finish()

class PrintTest(IsolatedAsyncioTestCase):
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
        self.patch = Patch('default', '', None, NaiveScope(), 'default')
        self.pr = await mkproc(self, "print")
        self.out = await mkproc(self, "var")
        await self.pr.connect(0, self.out, 0)

    async def test_default(self):
        '''[print] uses default formatter'''

        await self.pr.send("hello, world")
        assert self.out.outlets[0] == "hello, world"

        await self.pr.send(123)
        assert self.out.outlets[0] == "123"

    async def test_string_format(self):
        '''[print] will use format given on inlet 1'''

        await self.pr.send("%.3s", 1)
        await self.pr.send(False)
        assert self.out.outlets[0] == "Fal"

    async def test_seq_format(self):
        '''[print] will apply tuple to multiple args, but not list'''

        await self.pr.send("%s %s %s", 1)
        await self.pr.send([1, 2, 3])

        assert self.out.outlets[0] == "%s %s %s [1, 2, 3]"

        await self.pr.send((1, 2, 3))

        assert self.out.outlets[0] == "1 2 3"

    async def asyncTearDown(self):
        await MFPApp().finish()

class RouteTest (IsolatedAsyncioTestCase):
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
        self.r = await mkproc(self, "route", 'False, 1, "hello"')

    async def test_basic_routing(self):
        '''[route] works in simple cases'''
        await self.r.send([False, True], 0)
        assert self.r.outlets[0] == [True]
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == Uninit

        await self.r.send([1, 2, 3], 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == [2, 3]
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == Uninit

        await self.r.send((1, 2, 3), 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == (2, 3)
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == Uninit

        await self.r.send('hello', 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Bang
        assert self.r.outlets[3] == Uninit

        await self.r.send('unmatched', 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == 'unmatched'

        await self.r.send(['unmatched', 2], 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == ['unmatched', 2]

    async def test_reset_addresses(self):
        '''[route] can change its addresses on the fly '''
        await self.r.send([1, 2], 1)
        await self.r.send([1, True], 0)
        assert len(self.r.outlets) == 3

        assert self.r.outlets[0] == [True]
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit

        await self.r.send([2, False], 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == [False]
        assert self.r.outlets[2] == Uninit

        await self.r.send('unmatched', 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == 'unmatched'

    async def test_connections_ok(self):
        '''[route] --> [var] connection remains when addresses resized'''
        v = await mkproc(self, "var")
        await self.r.connect(0, v, 0)
        await self.r.send([4], 1)
        await self.r.send([4, 'hello'], 0)
        assert v.outlets[0] == ['hello']

    async def asyncTearDown(self):
        await MFPApp().finish()
