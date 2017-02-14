#! /usr/bin/env python
'''
utils.py
Various utility routines not specific to MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import cProfile
from threading import Thread, Lock, Condition
import time
from mfp import log
from datetime import datetime, timedelta


def homepath(fn):
    import os.path
    import os
    return os.path.join(os.environ.get("HOME", "~"), fn)


def splitpath(p):
    if not p:
        return []
    parts = p.split(":")
    unescaped = []
    prefix = None
    for p in parts:
        if not p:
            continue
        if p[-1] == '\\':
            newpart = p[:-1] + ':'
            if prefix is not None:
                prefix = prefix + newpart
            else:
                prefix = newpart
        elif prefix is None:
            unescaped.append(p)
        else:
            unescaped.append(prefix + p)
            prefix = None
    return unescaped


def joinpath(elts):
    parts = []
    for e in elts:
        parts.append(e.replace(':', '\\:'))

    return ':'.join(parts)


def find_file_in_path(filename, pathspec):
    import os.path
    import os
    searchdirs = splitpath(pathspec)
    for d in searchdirs:
        path = os.path.join(d, filename)
        try:
            s = os.stat(path)
            if s:
                return path
        except:
            continue
    return None


def prepend_path(newpath, searchpath):
    searchdirs = splitpath(searchpath)
    if newpath in searchdirs:
        searchdirs.remove(newpath)
    searchdirs[:0] = [newpath]
    return joinpath(searchdirs)


def logcall(func):
    def wrapper(*args, **kwargs):
        from mfp import log
        if "log" not in func.__name__:
            log.debug("called: %s.%s (%s)" % (type(args[0]).__name__, func.__name__, args[0]))
        return func(*args, **kwargs)

    return wrapper


def profile(func):
    '''
    Decorator to profile the decorated function using cProfile

    Usage: To profile function foo,

            @profile
            def foo(*args):
                    pass
    '''

    def wrapper(*args, **kwargs):
        if not hasattr(func, 'profinfo'):
            setattr(func, 'profinfo', cProfile.Profile())

        p = getattr(func, 'profinfo')

        # Name the data file sensibly
        p.enable()
        retval = func(*args, **kwargs)
        p.disable()

        datafn = func.__name__ + ".profile"
        p.dump_stats(datafn)
        return retval

    return wrapper


def extends(klass):
    '''
    Decorator applied to methods defined outside the
    scope of a class declaration.

    Usage: To add a method meth to class Foo,

            @extends(Foo)
            def meth(self, *args):
                    pass

    This creates a monkeypatch method so will probably not work for
    all purposes, but it does help in breaking up large files.  Need
    to add an import at the end of the class def file.
    '''

    def ext_decor(func):
        fn = func.__name__
        setattr(klass, fn, func)
        return func
    return ext_decor


def isiterable(obj):
    try:
        if hasattr(obj, '__iter__'):
            return True
    except:
        pass

    return False

def catchall(thunk):
    from functools import wraps
    @wraps(thunk)
    def handled(*args, **kwargs):
        try:
            thunk(*args, **kwargs)
        except Exception as e:
            log.debug("Error in", thunk.__name__, e)
            log.debug_traceback()
    return handled 



class QuittableThread(Thread):
    _all_threads = []
    _all_threads_lock = None

    def __init__(self, target=None, args=()):
        self.join_req = False
        self.target = target

        if QuittableThread._all_threads_lock is None:
            QuittableThread._all_threads_lock = Lock()

        with QuittableThread._all_threads_lock:
            QuittableThread._all_threads.append(self)
        if self.target is not None:
            Thread.__init__(self, target=self.target, args=tuple([self] + list(args)))
        else:
            Thread.__init__(self)

    def finish(self):
        with QuittableThread._all_threads_lock:
            try:
                QuittableThread._all_threads.remove(self)
            except ValueError:
                print("QuittableThread.finish() error:", self, "not in _all_threads")
            except Exception as e:
                print("QuittableThread.finish() error:", self, e)
                print("Remaining threads:", QuittableThread._all_threads)
        self.join_req = True
        self.join()

    @classmethod
    def finish_all(klass):
        with QuittableThread._all_threads_lock:
            work = [t for t in QuittableThread._all_threads]
        for t in work:
            t.finish()

    @classmethod
    def wait_for_all(klass):
        next_victim = True

        while next_victim:
            if isinstance(next_victim, Thread) and next_victim.isAlive():
                next_victim.join(.2)
            with QuittableThread._all_threads_lock:
                living_threads = [
                    t for t in QuittableThread._all_threads
                    if t.isAlive()
                ]
                if len(living_threads) > 0:
                    next_victim = living_threads[0]
                else:
                    next_victim = False


class TaskNibbler (QuittableThread):
    class NoData (object):
        pass
    NODATA = NoData()

    def __init__(self):
        self.lock = Lock()
        self.cv = Condition(self.lock)
        self.queue = []
        self.failed = []
        QuittableThread.__init__(self)
        self.start()

    def run(self):
        work = []
        retry = []

        while not self.join_req:
            with self.lock:
                self.cv.wait(0.25)
                work = []
                if self.queue:
                    work.extend(self.queue)
                    self.queue = []

                if self.failed:
                    toonew = []
                    newest = datetime.utcnow() - timedelta(milliseconds=250)
                    for jobs, timestamp in self.failed:
                        if timestamp < newest:
                            work.extend(jobs)
                        else:
                            toonew.append((jobs, timestamp))
                    self.failed = toonew
            retry = []
            for unit, retry_count, data in work:
                try:
                    done = unit(*data)
                except Exception as e:
                    log.debug("Exception while running", unit)
                    log.debug_traceback()

                if not done and retry_count:
                    if isinstance(retry_count, (int, float)):
                        if retry_count > 1:
                            retry_count -= 1
                        else:
                            log.warning("[TaskNibbler] ran out of retries for", unit, data)
                            retry_count = False
                    retry.append((unit, retry_count, data))

            if retry:
                with self.lock:
                    self.failed.append((retry, datetime.utcnow()))

    def add_task(self, task, retry, *data):
        with self.lock:
            self.queue.append((task, retry, data))
            self.cv.notify()
