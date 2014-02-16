
import sys
import time 

from rpc_listener import RPCListener 
from rpc_host import RPCHost 
from rpc_wrapper import RPCWrapper, rpcwrap

role = "server" 

class ProxyTest (RPCWrapper): 
    @rpcwrap
    def foo(self):
        print "ProxyTest.foo() local", role
        return role 

def main(): 
    host = RPCHost()
    host.start()
    RPCWrapper.rpchost = host 
    listener = RPCListener(sys.argv[1], "server", host)
    listener.start() 

    print "server: created listener" 

    host.publish(ProxyTest)

    print "server: serving ProxyTest objects"

    while True: 
        time.sleep(1)

if __name__ == "__main__":
    main()

