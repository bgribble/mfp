#! /usr/bin/env python
'''
utils.py
Various utility routines not specific to MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import cProfile

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

def profile(func):
    '''
    Decorator to profile the decorated function using cProfile

    Usage: To profile function foo,

            @profile
            def foo(*args):
                    pass
    '''

    def wrapper(*args, **kwargs):
        # Name the data file sensibly
        datafn = func.__name__ + ".profile"
        prof = cProfile.Profile()
        retval = prof.runcall(func, *args, **kwargs)
        prof.dump_stats(datafn)
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

from threading import Thread, Lock

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
                print "QuittableThread.finish() error:", self, "not in _all_threads"
            except Exception, e: 
                print "QuittableThread.finish() error:", self, e 
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
