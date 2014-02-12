import socket 
import sys
import os 

from mfp.utils import QuittableThread 

class RPCListener (QuittableThread): 
    '''
    RPCListener -- listen for incoming connections on a UNIX socket, 
    hand off to an RPCHost 
    '''

    def __init__(self, socketpath, name, rpc_host):
        QuittableThread.__init__(self)
        self.socketpath = socketpath
        self.socket = None 
        self.name = name 
        self.rpc_host = rpc_host 

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
                sock.settimeout(None)
                self.rpc_host.manage(sock, addr)

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




        
