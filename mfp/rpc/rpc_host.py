import time 
import simplejson as json 
import threading 

from request import Request 
from rpc_wrapper import RPCWrapper 
from mfp.utils import QuittableThread
from worker_pool import WorkerPool 

def blather(func):
    from datetime import datetime
    def inner(self, *args, **kwargs):
        if self.node_id in (1, None):
            print "%s DEBUG %s -- enter" % (datetime.now(), func.__name__)
        rv = func(self, *args, **kwargs)
        if self.node_id in (1, None):
            print "%s DEBUG %s -- leave (%s)" % (datetime.now(), func.__name__,  rv)
        return rv
    return inner


class RPCHost (QuittableThread): 
    '''
    RPCHost -- create and manage connections and proxy objects.  Both client and 
    server need an RPCHost, one per process.   
    '''
    SYNC_MAGIC = "[ SYNC ]"

    class SyncError (Exception): 
        pass

    class RecvError (Exception):
        pass 

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
            if oldsock.fileno() in self.fdsockets:
                del self.fdsockets[oldsock.fileno()]

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
     
    def unpublish(self, cls):
        cls.local = False 
        cls.rpchost = None 
        del self.served_classes[cls.__name__]
        self.notify_all()

    def subscribe(self, cls):
        '''
        RPCHost.subscribe: Wait for a class to become available
        '''
        while not cls.publishers:
            time.sleep(0.1)

    def put(self, req, peer_id):
        from datetime import datetime

        # find the right socket 
        sock = self.managed_sockets.get(peer_id)
        if sock is None: 
            print "[%s] RPCHost.put: peer_id %s has no mapped socket" % (datetime.now(),
                                                                         peer_id)
            print req.serialize()
            raise Exception()
    
        # is this a request?  if so, put it in the pending dict 
        if req.method is not None:
            self.pending[req.request_id] = req
            req.state = Request.SUBMITTED 

        # write the data to the socket 
        jdata = req.serialize()
        try:
            with self.lock: 
                sock.send(self.SYNC_MAGIC)
                sock.send("% 8d" % len(jdata))
                sock.send(jdata)
        except Exception, e:
            print "[%s] RPCHost.put: SEND error: %s" % (datetime.now(), e)
            print jdata 
            raise Exception()

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
        #print '    [%s --> %s] %s' % (peer_id, self.node_id, json_data)

        #py_data = json.loads("[" + json_data.replace("}{", "}, {") + "]")
        obj = json.loads(json_data)
        req = Request.from_dict(obj)
    
        # is someone waiting on this response? 
        if req.is_response() and req.request_id in self.pending:
            oldreq = self.pending.get(req.request_id)
            oldreq.result = req.result 
            oldreq.state = req.state
            oldreq.diagnostic = req.diagnostic
            with self.lock:
                self.condition.notify()
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

        while not self.join_req:
            rdy = None 
            for s in self.managed_sockets.values(): 
                if s.fileno() not in self.fdsockets: 
                    self.fdsockets[s.fileno()] = s  
            try: 
                sockets = self.fdsockets.keys()
                if sockets: 
                    rdy, _w, _x = select.select(self.fdsockets.keys(), [], [], 0.1)
                else: 
                    time.sleep(0.1)
            except Exception, e: 
                print "select exception:", e

            if not rdy: 
                continue
            jdata = None 
            syncbytes = 8
            sync = ''
            for rsock in rdy: 
                retry = 1 
                while retry: 
                    sock = self.fdsockets.get(rsock)
                    if sock is None: 
                        retry = 0
                        jdata = None 
                        continue 

                    try: 
                        sync = sync[syncbytes:]
                        syncbit = sock.recv(syncbytes)
                        if not syncbit:
                            raise self.RecvError()
                        sync += syncbit  
                        if sync != RPCHost.SYNC_MAGIC: 
                            syncbytes = 1
                            retry = 1
                            raise self.SyncError()
                        else:
                            syncbytes = 8
                            retry = 0
                        jlen = sock.recv(8)
                        jlen = int(jlen)
                        jdata = sock.recv(jlen)
                    except RPCHost.SyncError, e: 
                        print "RpcHost: sync error, resyncing"
                        pass
                    except RPCHost.RecvError, e: 
                        print "RPCHost: recv() error, blacklisting", sock
                        retry = 0 
                        jdata = None 
                        del self.fdsockets[rsock]
                        del self.peers_by_socket[sock] 
                        for k, v in self.managed_sockets.items(): 
                            if v == sock: 
                                print "RPCHost: deleting", k
                                del self.managed_sockets[k]
                                break
                    except Exception, e: 
                        print "RPCHost: caught exception",  e
                        print jdata 
                        retry = 0
                        jdata = ""

                    if jdata is not None and len(jdata):
                        peer_id = self.peers_by_socket.get(sock)
                        self.read_workers.submit((jdata, peer_id))
            
        if self.node_id == 0: 
            req = Request("exit_request", {})
            peers = self.managed_sockets.keys()
            for node in peers:
                self.put(req, node)
                self.wait(req)
                del self.managed_sockets[node]

        elif 0 in self.managed_sockets:
            req = Request("exit_notify", {})
            self.put(req, 0)
            self.wait(req)


        for clsname, cls in self.served_classes.items(): 
            self.unpublish(cls)

        for clsname, cls in RPCWrapper.rpctype.items():
            cls.publishers = []

        if RPCWrapper.rpchost == self: 
            RPCWrapper.rpchost = None 

        self.read_workers.finish()

    def handle_request(self, req, peer_id):
        from datetime import datetime 

        method = req.method 
        rpcdata = req.params
        rpcid = rpcdata.get('rpcid')
        args = rpcdata.get('args') or [] 
        kwargs = rpcdata.get('kwargs') or {}

        req.state = Request.RESPONSE_DONE

        req.diagnostic['local_call_started'] = str(datetime.now())

        if method == 'create':
            factory = RPCWrapper.rpctype.get(rpcdata.get('type'))
            if factory:
                obj = factory(*args, **kwargs)
                req.result = (True, obj.rpcid)
            else:
                req.result = (RPCWrapper.NO_CLASS, None)
        elif method == 'delete':
            del RPCWrapper.objects[rpcid]
            req.result = (True, None)
        elif method == 'call':
            obj = RPCWrapper.rpcobj.get(rpcid)
            try:
                retval = obj.call_locally(rpcdata)
                req.result = (RPCWrapper.METHOD_OK, retval)
            except RPCWrapper.MethodNotFound, e:
                req.result = (RPCWrapper.NO_METHOD, None)
            except RPCWrapper.MethodFailed, e:
                req.result = (RPCWrapper.METHOD_FAILED, e.traceback)
            except Exception, e:
                import traceback
                einfo = ("Method call failed rpcid=%s node=%s\nobj=%s data=%s\n" % 
                         (rpcid, peer_id, obj, rpcdata))
                req.result = (RPCWrapper.METHOD_FAILED, einfo + traceback.format_exc())

        elif method == 'publish': 
            for clsname in req.params.get("classes"): 
                cls = RPCWrapper.rpctype.get(clsname)
                if cls is not None:
                    cls.publishers.append(peer_id)
            req.result = (True, None) 

        elif method == "ready":
            req.result = (True, peer_id)

        elif method == "exit_request":
            if not self.join_req:
                self.finish()
            req.request_id = None

        elif method == "exit_notify": 
            # remove this peer as a publisher for any classes
            for clsname, cls in RPCWrapper.rpctype.items():
                if peer_id in cls.publishers:
                    cls.publishers.remove(peer_id)
            self.unmanage(peer_id) 
            req.request_id = None

        elif method == "node_status":
            pass

        else:
            print "rpc_wrapper: WARNING: no handler for method '%s'" % method
            print "call data:", rpcid, method, rpcdata

        req.method = None 
        req.params = None 

        req.diagnostic['local_call_complete'] = str(datetime.now())






