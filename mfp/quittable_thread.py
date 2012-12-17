
from threading import Thread, Lock


class QuittableThread(Thread):
    _all_threads = []
    _all_threads_lock = Lock()

    def __init__(self, target=None):
        self.join_req = False
        self.target = None
        with QuittableThread._all_threads_lock:
            QuittableThread._all_threads.append(self)
        if self.target is not None:
            Thread.__init__(self, target=self.target, args=(self,))
        else:
            Thread.__init__(self)

    def finish(self):
        with QuittableThread._all_threads_lock:
            QuittableThread._all_threads.remove(self)
        self.join_req = True
        self.join()

    @classmethod
    def finish_all(klass):
        with QuittableThread._all_threads_lock:
            work = [ t for t in QuittableThread._all_threads ]

        for t in work:
            t.finish()
