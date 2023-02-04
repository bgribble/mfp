#! /usr/bin/env python
'''
utils.py
Various utility routines not specific to MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import asyncio
import inspect
import cProfile
from threading import Thread, Lock, Condition
from mfp import log
from datetime import datetime, timedelta

def task(coro):
    asyncio.create_task(coro)

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
        except Exception:
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
    except Exception:
        pass

    return False


def catchall(thunk):
    from functools import wraps

    @wraps(thunk)
    def handled(*args, **kwargs):
        try:
            return thunk(*args, **kwargs)
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
            if isinstance(next_victim, Thread) and next_victim.is_alive():
                next_victim.join(.2)
            with QuittableThread._all_threads_lock:
                living_threads = [
                    t for t in QuittableThread._all_threads
                    if t.is_alive()
                ]
                if len(living_threads) > 0:
                    next_victim = living_threads[0]
                else:
                    next_victim = False

    @classmethod
    async def await_all(klass):
        all_dead = asyncio.Event()

        def _killer_thread():
            klass.wait_for_all()
            all_dead.set()

        t = Thread(target=_killer_thread)
        t.start()
        await all_dead.wait()
        t.join()


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
                except Exception:
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


def log_monitor(message, log_module, debug=False):
    message = message.strip()
    if message.startswith("[LOG] "):
        message = message[6:]
        if message.startswith("FATAL:"):
            log.error(message[7:], module=log_module)
        elif message.startswith("ERROR:"):
            log.error(message[7:], module=log_module)
        elif message.startswith("WARNING:"):
            log.warning(message[9:], module=log_module)
        elif message.startswith("INFO:"):
            log.info(message[6:], module=log_module)
        elif message.startswith("DEBUG:"):
            log.debug(message[7:], module=log_module)
    elif message.startswith("JackEngine::XRun"):
        log.warning("JACK: " + message, module=log_module)
    elif message.startswith("JackAudioDriver"):
        if "Process error" in message:
            log.error("JACK: " + message, module=log_module)
    elif debug and len(message):
        log.debug("%s " % log_module, message)


class AsyncExecMonitor:
    '''
    AsyncExecMonitor -- launch a process which will connect back to this process
    and listen to its output
    '''

    def __init__(self, command, *args, **kwargs):
        from mfp import log
        self.exec_file = command
        self.exec_args = list(args)
        self.process = None
        self.monitor_task = None

        if "log_module" in kwargs:
            self.log_module = kwargs["log_module"]
        else:
            self.log_module = log.log_module

        if kwargs.get("log_raw"):
            self.log_raw = True
        else:
            self.log_raw = False

    async def start(self):
        from mfp import log
        import shutil

        execfile = shutil.which(self.exec_file)
        self.callback = log_monitor
        self.process = await asyncio.create_subprocess_exec(
            execfile, *[str(a) for a in self.exec_args],
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        self.monitor_task = asyncio.create_task(self.monitor())

    async def monitor(self):
        while True:
            try:
                nextline = await self.process.stdout.readline()
                nextline = nextline.decode().strip()

                if not nextline:
                    continue

                cb_return = self.callback(nextline, self.log_module, self.log_raw)
                if inspect.isawaitable(cb_return):
                    await cb_return

            except asyncio.CancelledError:
                log.debug("AsyncExecMonitor: task cancelled")
                break

            except Exception as e:
                log.debug("AsyncExecMonitor: exiting with error", e)
                break


    async def cancel(self):
        self.process.terminate()
        self.monitor_task.cancel()
        await self.process.wait()
        await self.monitor_task
