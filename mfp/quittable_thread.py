
from threading import Thread, Lock


class QuittableThread(Thread):
    _all_threads = []
    _all_threads_lock = Lock()

    def __init__(self, target=None):
        self.join_req = False
        self.target = target

        with QuittableThread._all_threads_lock:
            QuittableThread._all_threads.append(self)
        if self.target is not None:
            Thread.__init__(self, target=self.target, args=(self,))
        else:
            Thread.__init__(self)

    def finish(self):
        with QuittableThread._all_threads_lock:
            try:
                QuittableThread._all_threads.remove(self)
            except ValueError:
                print "QuittableThread error:", self, "not in _all_threads"
            except Exception, e: 
                print "QuittableThread error:", self, e 
                print "Remaining threads:", QuittableThread._all_threads
        
        self.join_req = True
        self.join()

    @classmethod
    def finish_all(klass):
        with QuittableThread._all_threads_lock:
            work = [ t for t in QuittableThread._all_threads ]
        for t in work:
            t.finish()

    @classmethod
    def wait_for_all(klass):
        next_victim = True 

        while next_victim:
            if isinstance(next_victim, Thread):
                next_victim.join(timeout=0.2)
            with QuittableThread._all_threads_lock:
                if len(QuittableThread._all_threads) > 0:
                    next_victim = QuittableThread._all_threads[0]
                else:
                    next_victim = False  
