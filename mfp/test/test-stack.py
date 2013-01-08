
from unittest import TestCase
from mfp.main import MFPApp
from mfp.patch import Patch
from mfp import Bang
from mfp.processor import Processor


def mkproc(case, init_type, init_args=None):
    return MFPApp().create(init_type, init_args, case.patch, None, init_type)


class LimitedIncr (Processor):
    def __init__(self, patch, limit=0):
        self.limit = limit
        self.lastval = None
        Processor.__init__(self, 1, 1, 'limitedincr', '', patch, None, None)

    def trigger(self):
        if self.inlets[0] < self.limit:
            self.outlets[0] = self.inlets[0] + 1
            self.lastval = self.outlets[0]


class FanOut (Processor):
    trail = []

    def __init__(self, patch, tag):
        self.patch = Patch('default', '', None, None, 'default')
        self.tag = tag
        Processor.__init__(self, 1, 4, "fanout", '', patch, None, None)

    def trigger(self):
        self.outlets[0] = self.outlets[1] = self.outlets[2] = self.outlets[3] = Bang
        FanOut.trail.append(self.tag)


class StackDepthTest(TestCase):
    def setUp(self):
        self.patch = Patch('default', '', None, None, 'default')
        self.var = mkproc(self, "var", "0")
        self.inc = LimitedIncr(self.patch)
        self.var.connect(0, self.inc, 0)
        self.inc.connect(0, self.var, 0)

    def test_100(self):
        '''test_100: 100 recursions doesn't overflow stack'''
        self.inc.limit = 100
        self.var.send(0, 0)
        print "Last value:", self.inc.lastval
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 100)

    def test_1000(self):
        '''test_1000: 1000 recursions doesn't overflow stack'''
        self.inc.limit = 1000
        self.var.send(0, 0)
        print "Last value:", self.inc.lastval
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 1000)

    def test_10000(self):
        '''test_10000: 10000 recursions doesn't overflow stack'''
        self.inc.limit = 10000
        self.var.send(0, 0)
        print "Last value:", self.inc.lastval
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 10000)

    def test_100000(self):
        '''test_100000: 100000 recursions doesn't overflow stack'''
        self.inc.limit = 100000
        self.var.send(0, 0)
        print "Last value:", self.inc.lastval
        self.assertEqual(self.var.status, Processor.READY)
        self.assertEqual(self.inc.lastval, 100000)


class DepthFirstTest(TestCase):
    def setUp(self):
        self.patch = Patch('default', '', None, None, 'default')
        FanOut.trail = []
        self.procs = [FanOut(self.patch, i) for i in range(0, 10)]
        for i in range(1, 5):
            self.procs[0].connect(i - 1, self.procs[i], 0)
        for i in range(5, 9):
            self.procs[1].connect(i - 5, self.procs[i], 0)
        self.procs[3].connect(0, self.procs[9], 0)

    def test_depthfirst(self):
        '''test_depthfirst: depth-first execution order is preserved'''
        self.procs[0].send(Bang, 0)
        print FanOut.trail
        self.assertEqual(FanOut.trail, [0, 1, 5, 6, 7, 8, 2, 3, 9, 4])
