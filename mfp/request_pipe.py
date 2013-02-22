#! /usr/bin/env python2.6
'''
request_pipe.pt
Duplex multiprocessing pipe implementation with request/response model
'''
import multiprocessing
import threading
import Queue

from request import Request
from worker_pool import WorkerPool, BaseWorker
from . import log


class RequestWorker (BaseWorker):
    def __init__(self, pool, pipe):
        self.pipe = pipe
        BaseWorker.__init__(self, pool)

    def take_work(self):
        try:
            bite = self.pipe.get(timeout=0.1)
            return bite
        except Queue.Empty:
            raise WorkerPool.Empty()

    def perform_work(self, bite):
        req = self.pipe.process(bite)

        if req.payload == 'quit':
            # escape takes this thread out of the pool for finish()
            self.escape()
            self.pool.finish()
            # returning False kills this thread
            return False
        return True


class RequestPipe(object):
    def __init__(self, factory=None):
        master, slave = multiprocessing.Pipe()

        self.role = None
        self.running = True 

        # the slave will switch these
        self.this_end = master
        self.that_end = slave

        # management objects for those waiting for a response
        self.lock = None
        self.condition = None
        self.pending = {}

        if factory is None:
            factory = lambda pool: RequestWorker(pool, self)
        self.reader = WorkerPool(factory)

        # not normally used
        self.handler = None

        self.finish_callbacks = []

    def on_finish(self, cbk):
        self.finish_callbacks.append(cbk)

    def finish(self):
        self.running = False 

        if self.reader:
            self.reader.finish()
        for cbk in self.finish_callbacks:
            cbk()

        with self.lock:
            self.condition.notify_all()

    def init_master(self):
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.role = 1

        self.reader.start()

    def init_slave(self):
        '''Reverse ends of pipe; to be used by the slave process'''
        q = self.this_end
        self.this_end = self.that_end
        self.that_end = q
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.role = 0

        self.reader.start()

    def put(self, req):
        if not self.running:
            return req 

        tosend = {}
        if isinstance(req, Request):
            if req.state == Request.CREATED:
                self.pending[req.request_id] = req
                origin = self.role
                req.state = Request.SUBMITTED
            else:
                origin = 0 if self.role else 1
                req.state = Request.SUBMITTED

            req.queue = self
            tosend['type'] = 'Request'
            tosend['request_id'] = req.request_id
            tosend['payload'] = req.payload
            tosend['response'] = req.response
            tosend['origin'] = origin
        else:
            tosend['type'] = 'payload'
            tosend['payload'] = req
        self.this_end.send(tosend)

        return req

    def wait(self, req):
        if not self.running:
            return False 

        if not isinstance(req, Request):
            return False

        with self.lock:
            while req.state != Request.RESPONSE_RCVD:
                self.condition.wait()
                if not self.running: 
                    return False 

    def get(self, timeout=None):
        if not self.running:
            return None

        if timeout is not None:
            ready = self.this_end.poll(timeout)
            if not ready:
                raise Queue.Empty
        try:
            qobj = self.this_end.recv()
            return qobj
        except EOFError, e:
            raise Queue.Empty

    def process(self, qobj):
        if not self.running:
            return None

        req = None
        if qobj.get('type') == 'Request':
            if self.pending is not None and qobj.get('origin') == self.role:
                req = self.pending.get(qobj.get('request_id'))
            else:
                req = None
            if req:
                req.response = qobj.get('response')
                req.payload = qobj.get('payload')
                req.state = Request.RESPONSE_RCVD
                del self.pending[req.request_id]
                if req.callback is not None:
                    req.callback(req)
            elif qobj.get('origin') != self.role:
                req = Request(qobj.get('payload'))
                req.request_id = qobj.get('request_id')
                req.state = Request.RESPONSE_PEND
            qobj = req
        else:
            qobj = qobj.get('payload')
            if self.handler is not None:
                self.handler(self, qobj)

        with self.lock:
            self.condition.notify_all()
        return qobj
