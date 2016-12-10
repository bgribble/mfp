import socket 
import sys
import os 
import select

from mfp.utils import QuittableThread 
from mfp import log
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
        from mfp import log 
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
                log.debug("accept: got", sock, addr)
                sock.settimeout(0.25)
                self._rpc_last_peer += 1
                newpeer = self._rpc_last_peer
                self.rpc_host.manage(newpeer, sock)
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

        req = Request("ready", {})
        self.rpc_host.put(req, 0)
        self.rpc_host.wait(req)
        self.rpc_host.node_id = req.result[1]

    def close(self): 
        self.rpc_host.unmanage(0)
        self.socket.close()
        self.socket = None


class RPCExecRemote (QuittableThread):
    '''
    RPCExecRemote -- launch a process which will connect back to this process
    '''
    
    def __init__(self, exec_file, *args, **kwargs): 
        from mfp import log 
        QuittableThread.__init__(self)
        self.exec_file = exec_file 
        self.exec_args = list(args)
        self.process = None 
        if kwargs.has_key("log_module"):
            self.log_module = kwargs["log_module"]
        else:
            self.log_module = log.log_module

        if kwargs.get("log_raw"): 
            self.log_raw = True
        else: 
            self.log_raw = False 

    def start(self):
        from mfp import log 
        import subprocess 
        arglist = [self.exec_file] + self.exec_args
        log.debug("RPCExecRemote: starting as ", arglist)
        self.process = subprocess.Popen([str(a) for a in arglist], bufsize=0,
                                        stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        QuittableThread.start(self)
         
    def run(self):
        from mfp import log 
        while not self.join_req: 
            try: 
                if self.process: 
                    fileobj = self.process.stdout
                    r, w, e = select.select([fileobj], [], [], 0.25)
                    if fileobj in r:
                        ll = fileobj.readline()
                    else: 
                        continue
                else: 
                    ll = None 

                if not ll: 
                    self.join_req = True 
                else:
                    ll = ll.strip()
                    if ll.startswith("[LOG] "):
                        ll = ll[6:]
                        if ll.startswith("FATAL:"):
                            log.error(ll[7:], module=self.log_module)
                            self.join_req = True 
                        elif ll.startswith("ERROR:"):
                            log.error(ll[7:], module=self.log_module)
                        elif ll.startswith("WARNING:"):
                            log.warning(ll[9:], module=self.log_module)
                        elif ll.startswith("INFO:"):
                            log.info(ll[6:], module=self.log_module)
                        elif ll.startswith("DEBUG:"):
                            log.debug(ll[7:], module=self.log_module)
                    elif ll.startswith("JackEngine::XRun"):
                        log.warning("JACK: " + ll, module=self.log_module)
                    elif ll.startswith("JackAudioDriver"):
                        if "Process error" in ll:
                            log.error("JACK: " + ll, module=self.log_module)
                    elif self.log_raw and len(ll):
                        log.debug("%s:" % self.log_module, ll)

            except Exception, e: 
                log.debug("RPCExecRemote: exiting with error", e)
                self.join_req = True 

        if self.process:
            self.process.terminate()
            self.process.wait()

    def finish(self):
        from mfp import log
        p = self.process 
        self.process = None 
        if p is not None:
            try: 
                p.terminate()
                p.wait()
            except OSError, e: 
                pass

        self.quit_req = True 
        QuittableThread.finish(self)

    def alive(self): 
        if not self.process:
            return False 
        else: 
            return not self.process.poll()

class RPCMultiRemote (object):
    '''
    RPCMultiRemote -- launch a process with multiprocessing which will connect 
    back to this process
    ''' 
    def __init__(self, thunk, *args):
        self.thunk = thunk 
        self.args = args
        self.process = None 

    def start(self):
        from multiprocessing import Process 
        self.process = Process(target=self.thunk, args=self.args)
        self.process.start()

    def finish(self):
        self.process.terminate()
        self.process.join()

    def alive(self): 
        if not self.process:
            return False 
        else: 
            return not self.process.is_alive()


