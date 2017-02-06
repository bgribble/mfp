#! /usr/bin/env python 

from mfp.rpc.rpc_wrapper import RPCWrapper, rpcwrap
from mfp.rpc.rpc_host import RPCHost
from mfp.rpc.rpc_listener import RPCRemote 
from mfp.utils import QuittableThread

import sys 

reverse_value = None

class ReverseClass(RPCWrapper):
    @rpcwrap
    def reverse(self):
        global reverse_value
        return reverse_value

    @rpcwrap
    def fail(self):
        return 1 / 0

class WrappedClass(RPCWrapper):
    def __init__(self, arg1, **kwargs):
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

def main():
    socketpath = sys.argv[1] 
    remote_host = RPCHost()
    remote_host.publish(WrappedClass)
    remote_host.publish(ReverseClass)
    remote_host.start()
    remote_conn = RPCRemote(socketpath, "RPCTests_remote", remote_host)
    remote_conn.connect()

    try: 
        QuittableThread.wait_for_all()
    except Exception as e:
        print("wait_for_all caught error")

if __name__ == "__main__":
    main()






