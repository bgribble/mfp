
from unittest import TestCase
from mfp.mfp_app import MFPApp
from mfp.patch import Patch
from mfp.bang import Bang, Uninit


def mkproc(case, init_type, init_args=None):
    return MFPApp().create(init_type, init_args, case.patch, None, init_type)


class PlusTest(TestCase):
    def setUp(self):
        self.patch = Patch('default', '', None, None, 'default')
        self.plus = mkproc(self, "+", None, )
        self.out = mkproc(self, "var")
        self.plus.connect(0, self.out, 0)

    def test_default(self):
        '''test with default creation args'''
        self.plus = mkproc(self, "+", "12")
        self.plus.connect(0, self.out, 0)
        self.plus.send(13, 0)
        print "outlets:", self.out.outlets
        assert self.out.outlets[0] == 25

        self.plus.send(99, 0)
        assert self.out.outlets[0] == 111

    def test_numbers(self):
        '''test_numbers: 23 + 32 == 55'''
        self.plus.send(23, 1)
        self.plus.send(32, 0)
        assert self.out.outlets[0] == 55

    def test_strings(self):
        '''test_strings: 'hello ' + 'world' == 'hello world' '''
        self.plus.send("world", 1)
        self.plus.send("hello ", 0)
        assert self.out.outlets[0] == "hello world"

    def test_typeerr(self):
        '''test_typeerr: mismatched types produce nothing'''
        self.plus.send("hello", 1)
        self.plus.send(5, 0)

        assert self.out.outlets[0] is Uninit


class PrintTest(TestCase):
    def setUp(self):
        self.patch = Patch('default', '', None, None, 'default')
        self.pr = mkproc(self, "print")
        self.out = mkproc(self, "var")
        self.pr.connect(0, self.out, 0)

    def test_default(self):
        '''[print] uses default formatter'''

        self.pr.send("hello, world")
        assert self.out.outlets[0] == "hello, world"

        self.pr.send(123)
        assert self.out.outlets[0] == "123"

    def test_string_format(self):
        '''[print] will use format given on inlet 1'''

        self.pr.send("%.3s", 1)
        self.pr.send(False)
        assert self.out.outlets[0] == "Fal"

    def test_seq_format(self):
        '''[print] will apply tuple to multiple args, but not list'''

        self.pr.send("%s %s %s", 1)
        self.pr.send([1, 2, 3])

        assert self.out.outlets[0] == "%s %s %s [1, 2, 3]"

        self.pr.send((1, 2, 3))

        assert self.out.outlets[0] == "1 2 3"


class RouteTest (TestCase):
    def setUp(self):
        self.patch = Patch('default', '', None, None, 'default')
        self.r = mkproc(self, "route", 'False, 1, "hello"')

    def test_basic_routing(self):
        '''[route] works in simple cases'''
        self.r.send([False, True], 0)
        assert self.r.outlets[0] == [True]
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == Uninit

        self.r.send([1, 2, 3], 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == [2, 3]
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == Uninit

        self.r.send((1, 2, 3), 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == (2, 3)
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == Uninit

        self.r.send('hello', 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Bang
        assert self.r.outlets[3] == Uninit

        self.r.send('unmatched', 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == 'unmatched'

        self.r.send(['unmatched', 2], 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit
        assert self.r.outlets[3] == ['unmatched', 2]

    def test_reset_addresses(self):
        '''[route] can change its addresses on the fly '''
        self.r.send([1, 2], 1)
        self.r.send([1, True], 0)
        assert len(self.r.outlets) == 3

        assert self.r.outlets[0] == [True]
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == Uninit

        self.r.send([2, False], 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == [False]
        assert self.r.outlets[2] == Uninit

        self.r.send('unmatched', 0)
        assert self.r.outlets[0] == Uninit
        assert self.r.outlets[1] == Uninit
        assert self.r.outlets[2] == 'unmatched'

    def test_connections_ok(self):
        '''[route] --> [var] connection remains when addresses resized'''
        v = mkproc(self, "var")
        self.r.connect(0, v, 0)
        self.r.send([4], 1)
        self.r.send([4, 'hello'], 0)
        print self.r.addresses
        print v.outlets
        assert v.outlets[0] == ['hello']
