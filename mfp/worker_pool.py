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

    Implementations of BaseWorker have to define the take_work()
    and perform_work() methods
    '''

    def __init__(self, pool):
        self.pool = pool
        self.quit_req = False
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        self.thread = threading.Thread(target=self._thread_func)
        self.thread.start()

    def _thread_func(self):
        while not self.quit_req:
            # get in line
            self.pool.worker_ready(self)

            with self.lock:
                while not self.quit_req and self.pool.active_worker != self:
                    self.condition.wait()

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
        '''(virtual) Grab next available chunk of data'''
        pass

    def perform_work(self, data):
        '''(virtual) Process chunk of data'''
        pass

    def go(self):
        with self.lock:
            self.condition.notify()

    def exit(self):
        self.quit_req = True

    def finish(self):
        with self.lock:
            self.exit()
            self.condition.notify()


class WorkerPool (object):
    class Empty(Exception):
        pass

    def __init__(self, factory, count=5):
        self.factory = factory
        self.min_workers = count

        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)

        self.reaper = threading.Thread(target=self._reaper_thread)
        self.quit_req = False

        self.active_worker = None
        self.waiting_pool = []
        self.working_pool = []
        self.dead_pool = []

    def start(self):
        self.reaper.start()
        for n in range(self.min_workers):
            self.factory(self)

    def worker_ready(self, worker):
        with self.lock:
            if worker in self.working_pool:
                self.working_pool.remove(worker)
            if worker in self.waiting_pool:
                self.waiting_pool.remove(worker)

            if self.active_worker is None:
                self.active_worker = worker
            elif self.active_worker == worker:
                return
            else:
                if len(self.waiting_pool) < self.min_workers:
                    self.waiting_pool.append(worker)
                else:
                    worker.exit()
                    self.dead_pool.append(worker)
            self.condition.notify()

    def worker_consuming(self, worker):
        goworker = 0
        with self.lock:
            if worker == self.active_worker:
                self.working_pool.append(worker)
                if len(self.waiting_pool):
                    self.active_worker = self.waiting_pool.pop()
                    goworker = 1
                else:
                    self.active_worker = self.factory(self)
                    goworker = 1
            self.condition.notify()
        if goworker:
            self.active_worker.go()

    def worker_done(self, worker):
        with self.lock:
            if worker in self.waiting_pool:
                self.waiting_pool.remove(worker)
            if worker in self.working_pool:
                self.working_pool.remove(worker)
            if worker in self.dead_pool:
                self.dead_pool.remove(worker)
            self.dead_pool.append(worker)
            self.condition.notify()

    def _reaper_thread(self):
        deadworkers = []
        while not self.quit_req:
            with self.lock:
                self.condition.wait()
                if len(self.dead_pool):
                    deadworkers = self.dead_pool
                    self.dead_pool = []
            if len(deadworkers):
                for s in deadworkers:
                    s.thread.join()
                deadworkers = []

    def finish(self, wait=True):
        with self.lock:
            liveworkers = self.waiting_pool + self.working_pool + [self.active_worker]

        for s in liveworkers:
            s.finish()

        with self.lock:
            self.quit_req = True
            self.condition.notify()
        self.reaper.join()
