
from request import Request 
from rpc_wrapper import RPCWrapper 
from mfp.utils import QuittableThread
from worker_pool import WorkerPool 

class RPCHost (QuittableThread): 
    '''
    RPCHost -- create and manage connections and proxy objects.  Both client and 
    server need an RPCHost, one per process.   
    '''

    def __init__(self):
        QuittableThread.__init__(self)

        # FIXME -- one lock/condition per RPCHost means lots of 
        # unneeded waking up if lots of requests are queued 
        self.lock = None
        self.condition = None
        self.pending = {}

        self.served_classes = {}
        self.managed_sockets = {}  
        self.peers_by_socket = {} 
        self.managed_objects = {} 

        self.read_workers = WorkerPool(self.dispatch_rpcdata)
        
    def manage(self, peer_id, socket):
        if peer_id not in self.managed_sockets:
            self.managed_sockets[peer_id] = socket
            self.peers_by_socket[socket] = peer_id
            self.notify_peer(peer_id)

    def unmanage(self, peer_id):
        if peer_id in self.managed_sockets: 
            oldsock = self.managed_sockets[peer_id]
            del self.managed_sockets[peer_id]
            del self.peers_by_socket[oldsock]

    def notify_peer(self, peer_id): 
        req = Request("publish", dict(classes=self.served_classes.keys()))
        self.put(peer_id, req)

    def notify_all(self):
        for peer_id in self.managed_sockets:
            self.notify_peer(peer_id)

    def serve(self, cls):
        '''
        RPCHost.serve: Register a class as constructable on this end
        '''
        self.served_classes[cls.__name__] = cls 
        self.notify_all()
        
    def put(self, peer_id, req):

        # find the right socket 
        sock = self.managed_sockets.get(peer_id)

        # is this a request?  if so, put it in the pending dict 
        if req.method is not None:
            self.pending[req.request_id] = req
            req.state = Request.SUBMITTED 

        # write the data to the socket 
        jdata = req.serialize()
        sock.send(jdata)

    def wait(self, req):
        with self.lock:
            while req.state != Request.RESPONSE_RCVD:
                self.condition.wait(0.1)
                if not self.running: 
                    return False 

    def dispatch_rpcdata(self, rpc_worker, rpcdata):
        json_data, peer_id = rpcdata 
        req = Request.deserialize(json_data)
        
        # is someone waiting on this response? 
        if req.is_response() and req.request_id in self.pending:
            rpc_worker.pool.condition.notify()
        elif req.is_method() and req.request_id is not None:
            # actually call the local handler
            RPCWrapper.handle(req)

            # and send back the response 
            self.put(req, peer_id)

        return True

    def run(self):
        '''
        RPCHost.run: perform IO on managed sockets, dispatch data 
        '''

        import select 
        while not self.join_req:
            r_rdy, _, _ = select.select(self.managed_sockets, [], [])
            for rsock in r_rdy: 
                jdata = rsock.recv(4096)
                peer_id = self.peers_by_socket.get(rsock)
                self.read_workers.submit((jdata, peer_id))






