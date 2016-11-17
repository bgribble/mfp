#! /usr/bin/env python2.6
'''
worker_pool.py
Thread pool for processing units of work
'''

import threading

class BaseWorker (object):
    '''
    Each worker in the pool has a thread which waits for a signal on
    its condition variable.

    The thread calls self.take_work() to grab the next data chunk, 
    then perform_work() to consume it. 
    '''

    def __init__(self, pool, thunk=None):
        self.pool = pool
        self.thunk = thunk
        self.quit_req = False
        self.thread = threading.Thread(target=self._thread_func)
        self.thread.start()

    def _thread_func(self):
        workunit = None 
        while not self.quit_req:
            # get in line
            with self.pool.lock:
                if not self.pool.worker_ready(self):
                    break
                if not len(self.pool.submitted_data): 
                    self.pool.data_condition.wait()

                if self.quit_req:
                    break

                # take_work a chunk of data
                try:
                    workunit = self.take_work()
                except WorkerPool.Empty, e:
                    continue 

                # perform_work data
                self.pool.worker_consuming(self)
            keepalive = self.perform_work(workunit)
            if not keepalive:
                break
        self.pool.worker_done(self)

    def escape(self):
        with self.pool.lock:
            if self in self.pool.working_pool:
                self.pool.working_pool.remove(self)

    def take_work(self):
        '''Grab next available chunk of data'''
        with self.pool.lock: 
            if self.pool.submitted_data:
                rd = self.pool.submitted_data[0]
                self.pool.submitted_data = self.pool.submitted_data[1:] 
                return rd 
            else: 
                raise WorkerPool.Empty()

    def perform_work(self, data):
        '''Process chunk of data'''
        try:
            if callable(self.thunk): 
                return self.thunk(self, data)
        except Exception, e:
            import traceback
            traceback.print_exc()
            print e
            return True
        
    def exit(self):
        self.quit_req = True

class WorkerPool (object):
    class Empty(Exception):
        pass

    def __init__(self, factory, count=5):
        self.factory = factory
        self.min_workers = count

        self.lock = threading.RLock()
        self.reaper_condition = threading.Condition(self.lock)
        self.data_condition = threading.Condition(self.lock)

        self.reaper = threading.Thread(target=self._reaper_thread)
        self.quit_req = False

        self.submitted_data = []
        self.waiting_pool = []
        self.working_pool = []
        self.dead_pool = []

    def start(self):
        self.reaper.start()
        for n in range(self.min_workers):
            if isinstance(self.factory, type):
                self.factory(self)
            else: 
                BaseWorker(self, self.factory)

    def worker_ready(self, worker):
        with self.lock:
            if worker in self.working_pool:
                self.working_pool.remove(worker)
            if worker in self.waiting_pool:
                self.waiting_pool.remove(worker)

            if len(self.waiting_pool) < self.min_workers:
                self.waiting_pool.append(worker)
                return True 
            else:
                worker.exit()
                self.dead_pool.append(worker)
                self.reaper_condition.notify()
                return False 

    def worker_consuming(self, worker):
        with self.lock:
            if worker in self.working_pool:
                self.working_pool.remove(worker)
            if worker in self.waiting_pool:
                self.waiting_pool.remove(worker)

            self.working_pool.append(worker)
        if not self.quit_req and not len(self.waiting_pool):
            if isinstance(self.factory, type):
                self.factory(self)
            else: 
                BaseWorker(self, self.factory)

    def worker_done(self, worker):
        with self.lock:
            if worker in self.waiting_pool:
                self.waiting_pool.remove(worker)
            if worker in self.working_pool:
                self.working_pool.remove(worker)
            if worker in self.dead_pool:
                self.dead_pool.remove(worker)
            self.dead_pool.append(worker)
            self.reaper_condition.notify_all()

    def _reaper_thread(self):
        deadworkers = []
        while self.dead_pool or not self.quit_req:
            with self.lock:
                deadworkers = [] 
                if not self.dead_pool:
                    self.reaper_condition.wait(0.1)
                if self.dead_pool:
                    deadworkers = self.dead_pool
                    self.dead_pool = []
            if len(deadworkers):
                for s in deadworkers:
                    s.thread.join()
                deadworkers = []


    def submit(self, job_data):
        with self.lock:
            self.submitted_data.append(job_data)
            self.data_condition.notify()

    def finish(self, wait=True):
        with self.lock: 
            liveworkers = self.waiting_pool + self.working_pool 
            for s in liveworkers:
                s.exit()
                if s not in self.dead_pool:
                    self.dead_pool.append(s)
            self.waiting_pool = [] 
            self.working_pool = [] 

            self.quit_req = True 
            self.data_condition.notify_all()
            self.reaper_condition.notify_all()

        self.reaper.join()
