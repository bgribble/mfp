import sys 
import testserver 
from testserver import ProxyTest 
from rpc_listener import RPCRemote 
from rpc_host import RPCHost 
from rpc_wrapper import RPCWrapper 

host = RPCHost()
host.start()
RPCWrapper.rpchost = host 

print "client: started RPCHost"

remote = RPCRemote(sys.argv[1], "client", host)
remote.connect()

testserver.role = "client" 

print "client: connected RPCRemote"

p = ProxyTest()

print "client: constructed ProxyTest"

foo = p.foo()

print "client: p.foo() = ", foo 

host.join()
remote.close()
