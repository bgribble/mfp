import time 
import simplejson as json 
import threading 

from request import Request 
from rpc_wrapper import RPCWrapper 
from mfp.utils import QuittableThread, profile
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
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.pending = {}

        self.node_id = None 

        self.fdsockets = {} 

        self.served_classes = {}
        self.managed_sockets = {}  
        self.peers_by_socket = {} 
        self.managed_objects = {} 

        self.read_workers = WorkerPool(self.dispatch_rpcdata)
    
    def __repr__(self):
        return "<RPCHost node=%s>" % self.node_id

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
        req = Request("publish", dict(classes=self.served_classes.keys()))
        self.put(req, peer_id)
        self.wait(req)

    def notify_all(self):
        for peer_id in self.managed_sockets:
            self.notify_peer(peer_id)

    def publish(self, cls):
        '''
        RPCHost.publish: Register a class as constructable on this end
        '''
        self.served_classes[cls.__name__] = cls 
        cls.local = True 
        self.notify_all()
      
    def subscribe(self, cls):
        '''
        RPCHost.subscribe: Wait for a class to become available
        '''
        while not cls.publishers:
            time.sleep(0.1)

    def put(self, req, peer_id):
        # find the right socket 
        sock = self.managed_sockets.get(peer_id)
        if sock is None: 
            print self, "RPCHost.put: peer_id", peer_id, "has no mapped socket"
            raise Exception()

        # is this a request?  if so, put it in the pending dict 
        if req.method is not None:
            self.pending[req.request_id] = req
            req.state = Request.SUBMITTED 

        # write the data to the socket 
        jdata = req.serialize()
        sock.send(jdata)

    def wait(self, req, timeout=None):
        import datetime
        endtime = None
        if timeout is not None:
            endtime = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

        with self.lock:
            while req.state != Request.RESPONSE_RCVD:
                self.condition.wait(0.1)
                if self.join_req: 
                    return False 
                elif timeout is not None and datetime.datetime.now() > endtime: 
                    print "RPCHost.wait(): Request timed out after %s sec -- %s" % (timeout, req)
                    raise Exception()

    def dispatch_rpcdata(self, rpc_worker, rpcdata):
        json_data, peer_id = rpcdata 
        print self, "from node", peer_id, json_data

        py_data = json.loads("[" + json_data.replace("}{", "}, {") + "]")
        for obj in py_data: 
            req = Request.from_dict(obj)
        
            # is someone waiting on this response? 
            if req.is_response() and req.request_id in self.pending:
                oldreq = self.pending.get(req.request_id)
                oldreq.response = req.response 
                oldreq.state = req.state
                with rpc_worker.pool.lock:
                    rpc_worker.pool.condition.notify()
            elif req.is_request():
                # actually call the local handler
                self.handle_request(req, peer_id)
                # and send back the response                
                if req.request_id is not None:
                    self.put(req, peer_id)
        return True

    def run(self):
        '''
        RPCHost.run: perform IO on managed sockets, dispatch data 
        '''
        self.read_workers.start()

        if RPCWrapper.rpchost is None:
            RPCWrapper.rpchost = self

        import select 

        self.fdsockets = {} 
        errshown = False 

        while not self.join_req:
            for s in self.managed_sockets.values(): 
                if s.fileno() not in self.fdsockets: 
                    self.fdsockets[s.fileno()] = s  
            try: 
                rdy, _w, _x = select.select(self.fdsockets.keys(), [], [], 0.1)
            except Exception, e: 
                print "select exception:", e

            for rsock in rdy: 
                sock = self.fdsockets.get(rsock)
                try: 
                    jdata = sock.recv(4096)
                except Exception, e: 
                    print "RPCHost: caught exception", jdata 
                    jdata = ""

                if len(jdata):
                    peer_id = self.peers_by_socket.get(sock)
                    self.read_workers.submit((jdata, peer_id))
                    errshown = False 
            
        if 0 in self.managed_sockets:
            req = Request("peer_exit", {})
            self.put(req, 0)
            self.wait(req)
        print "rpc_host: join_req received, quitting worker_pool..."
        self.read_workers.finish()
        print "rpc_host: finished"

    def handle_request(self, req, peer_id):
        method = req.method 
        rpcdata = req.params
        rpcid = rpcdata.get('rpcid')
        args = rpcdata.get('args')
        kwargs = rpcdata.get('kwargs')

        req.state = Request.RESPONSE_DONE

        if method == 'create':
            factory = RPCWrapper.rpctype.get(rpcdata.get('type'))
            if factory:
                obj = factory(*args, **kwargs)
                req.response = (obj.rpcid, None)
            else:
                req.response = (RPCWrapper.NO_CLASS, None)
        elif method == 'delete':
            del RPCWrapper.objects[rpcid]
            req.response = (True, None)
        elif method == 'call':
            obj = RPCWrapper.rpcobj.get(rpcid)
            try:
                retval = obj.call_locally(rpcdata)
                req.response = (RPCWrapper.METHOD_OK, retval)
            except RPCWrapper.MethodNotFound, e:
                req.response = (RPCWrapper.NO_METHOD, None)
            except RPCWrapper.MethodFailed, e:
                req.response = (RPCWrapper.METHOD_FAILED, e.traceback)
            except Exception, e:
                import traceback
                einfo = ("Method call failed rpcid=%s node=%s\nobj=%s data=%s\n" % 
                         (rpcid, peer_id, obj, rpcdata))
                req.response = (RPCWrapper.METHOD_FAILED, einfo + traceback.format_exc())
        elif method == 'publish': 
            for clsname in req.params.get("classes"): 
                cls = RPCWrapper.rpctype.get(clsname)
                if cls is not None:
                    cls.publishers.append(peer_id)
            req.response = (True, None) 
        elif method == "node_id":
            self.node_id = req.params.get("node_id")
            req.response = (True, None)
        elif method == "peer_exit": 
            # remove this peer as a publisher for any classes
            for clsname, cls in RPCWrapper.rpctype.items():
                if peer_id in cls.publishers:
                    cls.publishers.remove(peer_id)
            self.unmanage(peer_id) 
            req.request_id = None

        elif method == "peer_status":
            pass

        else:
            print "rpc_wrapper: WARNING: no handler for method '%s'" % method
            print "call data:", rpcid, method, rpcdata

        req.method = None 
        req.params = None 







