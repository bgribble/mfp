
from request import Request 
from rpc_wrapper import RPCWrapper 
from mfp.utils import QuittableThread
from worker_pool import WorkerPool 
import simplejson as json 
import threading 

class RPCHost (QuittableThread): 
    '''
    RPCHost -- create and manage connections and proxy objects.  Both client and 
    server need an RPCHost, one per process.   
    '''

    def __init__(self):
        QuittableThread.__init__(self)

        # FIXME -- one lock/condition per RPCHost means lots of 
        # unneeded waking up if lots of requests are queued 
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.pending = {}
        
        self.pollobj = None
        self.poll_sockets = {} 

        self.served_classes = {}
        self.managed_sockets = {}  
        self.peers_by_socket = {} 
        self.managed_objects = {} 

        self.read_workers = WorkerPool(self.dispatch_rpcdata)
        
    def manage(self, peer_id, sock):
        if peer_id not in self.managed_sockets:
            self.managed_sockets[peer_id] = sock
            self.peers_by_socket[sock] = peer_id
            self.notify_peer(peer_id)

    def unmanage(self, peer_id):
        if peer_id in self.managed_sockets: 
            oldsock = self.managed_sockets[peer_id]
            del self.managed_sockets[peer_id]
            del self.peers_by_socket[oldsock]

    def notify_peer(self, peer_id): 
        print "RPCHost.notify_peer", peer_id, self.served_classes.keys()
        req = Request("publish", dict(classes=self.served_classes.keys()))
        self.put(req, peer_id)

    def notify_all(self):
        for peer_id in self.managed_sockets:
            self.notify_peer(peer_id)

    def serve(self, cls):
        '''
        RPCHost.serve: Register a class as constructable on this end
        '''
        self.served_classes[cls.__name__] = cls 
        self.notify_all()
        
    def put(self, req, peer_id):

        # find the right socket 
        sock = self.managed_sockets.get(peer_id)
        if sock is None: 
            print "RPCHost.put: peer_id", peer_id, "has no mapped socket"
            return 

        # is this a request?  if so, put it in the pending dict 
        if req.method is not None:
            self.pending[req.request_id] = req
            req.state = Request.SUBMITTED 

        # write the data to the socket 
        jdata = req.serialize()
        print "sending", jdata, "on", sock
        sock.send(jdata)

    def wait(self, req):
        with self.lock:
            while req.state != Request.RESPONSE_RCVD:
                self.condition.wait(0.1)
                print req, req.state
                if self.join_req: 
                    return False 

    def dispatch_rpcdata(self, rpc_worker, rpcdata):
        json_data, peer_id = rpcdata 
        py_data = json.loads("[" + json_data.replace("}{", "}, {") + "]")
        for obj in py_data: 
            req = Request.from_dict(obj)
        
            # is someone waiting on this response? 
            if req.is_response() and req.request_id in self.pending:
                rpc_worker.pool.condition.notify()
            elif req.is_request() and req.request_id is not None:
                # actually call the local handler
                RPCWrapper.handle(req)

                # and send back the response                
                self.put(req, peer_id)

        return True

    def run(self):
        '''
        RPCHost.run: perform IO on managed sockets, dispatch data 
        '''

        self.read_workers.start()

        import select 
        self.pollobj = select.poll() 
        for fd in (0,1,2):
            try:
                self.pollobj.unregister(fd)
            except KeyError:
                pass

        self.pollsockets = {} 
        errshown = False 

        print "rpc_host: run() started"
        while not self.join_req:
            for s in self.managed_sockets.values(): 
                if s.fileno() not in self.pollsockets: 
                    print "Adding", s, "to pollobj"
                    self.pollobj.register(s, select.POLLIN)
                    self.pollsockets[s.fileno()] = s  
            rdy = self.pollobj.poll(0.1)

            for rsock, event in rdy: 
                if event & select.POLLIN:
                    sock = self.pollsockets.get(rsock)
                    jdata = sock.recv(4096)
                    if len(jdata):
                        print "RPCHost.run: Got", jdata
                        peer_id = self.peers_by_socket.get(sock)
                        self.read_workers.submit((jdata, peer_id))
                        errshown = False 
                elif not errshown and event & (select.POLLERR | select.POLLHUP):
                    print "RPCHost.run: Socket error", event 
                    errshown = True 






