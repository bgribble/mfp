import socket 
import sys
import os 

from mfp.utils import QuittableThread 
from request import Request 

class RPCListener (QuittableThread): 
    '''
    RPCListener -- listen for incoming connections on a UNIX socket, 
    hand off to an RPCHost 
    '''
    _rpc_last_peer = 0 

    def __init__(self, socketpath, name, rpc_host):
        QuittableThread.__init__(self)
        self.socketpath = socketpath
        self.socket = None 
        self.name = name 
        self.rpc_host = rpc_host 
        self.rpc_host.node_id = 0

    def run(self): 
        # create socket 
        try:
            os.unlink(self.socketpath)
        except OSError:
            if os.path.exists(self.socketpath):
                raise                
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) 

        # set up to accept connections 
        self.socket.bind(self.socketpath)
        self.socket.listen(5)
        self.socket.settimeout(1)
        
        # accept connections until told to stop  
        while not self.join_req: 
            try: 
                sock, addr = self.socket.accept()
                sock.settimeout(0.0)
                self._rpc_last_peer += 1
                newpeer = self._rpc_last_peer
                self.rpc_host.manage(newpeer, sock)
                self.rpc_host.put(Request("node_id", dict(node_id=newpeer)), newpeer)  
            except socket.timeout:
                pass
        
class RPCRemote (object):
    '''
    RPCRemote -- connect to a RPCListener
    '''
    def __init__(self, socketpath, name, rpc_host):
        self.socketpath = socketpath 
        self.socket = None 
        self.name = name 
        self.rpc_host = rpc_host 

    def connect(self):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(self.socketpath)
        self.rpc_host.manage(0, self.socket)

    def close(self): 
        self.rpc_host.unmanage(0)
        self.socket.close()
        self.socket = None

class RPCExecRemote (object):
    '''
    RPCExecRemote -- launch a process which will connect back to this process
    '''
    def __init__(self, exec_file, *args): 
        self.exec_file = exec_file 
        self.exec_args = list(args)
        self.process = None 

    def start(self):
        import subprocess 
        arglist = [self.exec_file] + self.exec_args
        self.process = subprocess.Popen([str(a) for a in arglist])

    def finish(self):
        self.process.terminate()
        self.process.wait()

    def alive(self): 
        if not self.process:
            return False 
        else: 
            return not self.process.poll()

        
