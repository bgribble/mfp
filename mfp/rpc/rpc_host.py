import simplejson as json 
from mfp.utils import QuittableThread
from worker_pool import WorkerPool 

class RPCHost (QuittableThread): 
    '''
    RPCHost -- create and manage connections and proxy objects.  Both client and 
    server need an RPCHost, one per process.   
    '''

    def __init__(self):
        QuittableThread.__init__(self)
        self.served_classes = {}
        self.managed_sockets = [] 
        self.managed_objects = {} 
        self.read_workers = WorkerPool(self.dispatch_data)
        
    def manage(self, socket):
        if socket not in self.managed_sockets:
            self.managed_socket.append(socket)

    def unmanage(self, socket):
        if socket in self.managed_sockets: 
            self.managed_sockets.remove(socket)

    def serve(self, cls):
        '''
        RPCHost.serve: Register a class as constructable on this end
        '''
        self.served_sockets[cls.__name__] = cls 

    def dispatch_data(self, json_data):
        req = Request.deserialize(json_data)
        



    def run(self):
        '''
        RPCHost.run: perform IO on managed sockets, dispatch data 
        '''

        import select 
        while not self.join_req:
            r_rdy, _, _ = select.select(self.managed_sockets, [], [])
            for rsock in r_rdy: 
                jdata = rsock.recv(4096)
                self.read_workers.submit(jdata)






