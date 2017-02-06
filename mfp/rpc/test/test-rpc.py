from mfp.rpc.rpc_wrapper import RPCWrapper, rpcwrap
from mfp.rpc.rpc_host import RPCHost
from mfp.rpc.rpc_listener import RPCListener, RPCExecRemote

import time
from unittest import TestCase

from helper import WrappedClass, ReverseClass

class WrappedLocalClass(RPCWrapper):
    def __init__(self, arg1, **kwargs):
        print("WrappedLocalClass.__init__")
        self.arg = arg1
        RPCWrapper.__init__(self, arg1, **kwargs)

    @rpcwrap
    def retarg(self):
        return self.arg

    @rpcwrap
    def setarg(self, value):
        self.arg = value

    @rpcwrap
    def error_method(self):
        return 1 / 0


class Pinger(RPCWrapper):
    def __init__(self, volleys):
        RPCWrapper.__init__(self, volleys)
        if Pinger.local:
            self.volleys = volleys
            self.ponger = None
            if self.volleys > 0:
                self.ponger = Ponger(volleys - 1)

    @rpcwrap
    def ping(self):
        if self.ponger:
            return self.ponger.pong()
        else:
            return "PING"


class Ponger(RPCWrapper):
    def __init__(self, volleys):
        RPCWrapper.__init__(self, volleys)
        if Ponger.local:
            self.volleys = volleys
            self.pinger = None
            if self.volleys > 0:
                self.pinger = Pinger(volleys - 1)

    @rpcwrap
    def pong(self):
        if self.pinger:
            return self.pinger.ping()
        else:
            return "PONG"


class ReverseActivatorClass(RPCWrapper):
    @rpcwrap
    def reverse(self):
        print("Activator: ", ReverseActivatorClass.local, ReverseClass.local)
        o = ReverseClass()
        print("Activator:", o)
        return o.reverse()

def start_helper(sockname):
    import os.path
    helper = os.path.dirname(__file__) + "/helper.py"
    return RPCExecRemote(helper, sockname)

class RPCTests(TestCase):
    def setUp(self):
        print() 
        print("=== setup ===")
        import tempfile
        print("WrappedClass publishers:", WrappedClass.publishers)
        self.sockname = tempfile.mktemp()
        self.server = RPCHost()
        self.server.start()
        self.listener = RPCListener(self.sockname, "RPCTests", self.server)
        self.listener.start()
        self.remote = start_helper(self.sockname) 
        self.remote.start()
        self.server.publish(WrappedLocalClass)
        self.server.subscribe(WrappedClass)
        print("=== setup done ===")

    def tearDown(self):
        from datetime import datetime
        print()
        print("=== teardown ===")
        print("   teardown 1 %s" % datetime.now())
        self.server.finish()
        print("   teardown 2 %s" % datetime.now())
        self.listener.finish()
        print("   teardown 3 %s" % datetime.now())
        self.remote.finish()

        print("=== teardown done ===")

    def test_local(self):
        '''test_local: local calls on a RPCWrapper subclass work'''
        o = WrappedLocalClass("hello")
        print("test_local: WrappedLocal ctor returned")
        self.assertEqual(o.local, True)
        self.assertEqual(o.retarg(), "hello")
        o.setarg("goodbye")
        self.assertEqual(o.retarg(), "goodbye")
        print("test_local: ok")

    def test_remote(self):
        '''test_remote: calls on remote objects work'''
        print("About to create WrappedClass")
        o = WrappedClass(123.45)
        self.assertNotEqual(o.rpcid, None)
        try:
            self.assertEqual(o.retarg(), 123.45)
            o.setarg(dict(x=1, y=2))
            self.assertEqual(o.retarg(), dict(x=1, y=2))
        except RPCWrapper.MethodFailed as e:
            print('-------------------------')
            print(e.traceback)
            print('-------------------------')
            assert 0

    def test_badmethod(self):
        '''test_badmethod: failed method should raise MethodFailed'''
        failed = 0
        try:
            o = WrappedClass('foo')
            o.error_method()
        except RPCWrapper.MethodFailed as e:
            failed = 1
            print(e.traceback)

        self.assertEqual(failed, 1)
        print("test_badmethod: ok")
