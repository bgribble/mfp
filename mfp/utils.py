#! /usr/bin/env python
'''
utils.py
Various utility routines not specific to MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import asyncio
import inspect
import cProfile
import threading
from collections import defaultdict
from threading import Thread, Lock
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
            log.debug_traceback(e)
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
        if not QuittableThread._all_threads_lock:
            return

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
            if not QuittableThread._all_threads_lock:
                return
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
        loop = asyncio.get_event_loop()

        def _killer_thread():
            klass.wait_for_all()
            loop.call_soon_threadsafe(all_dead.set)

        t = Thread(target=_killer_thread)
        t.start()
        try:
            await all_dead.wait()
        except asyncio.exceptions.CancelledError:
            pass
        t.join()


class SignalMixin:
    """
    Add callback/emit capability to objects

    Not thread-safe but should be fine with asyncio
    """

    def __init__(self, *args, **kwargs):
        self.signal_handlers = defaultdict(list)
        self.handlers_by_id = {}
        self.last_handler_id = 0

    def signal_listen(self, signal, handler, *args):
        new_id = self.last_handler_id + 1
        self.last_handler_id = new_id
        old_handlers = self.signal_handlers[signal]
        old_handlers.append((new_id, handler, args))
        self.handlers_by_id[new_id] = signal
        return new_id

    def signal_unlisten(self, handler_id):
        signal = self.handlers_by_id.get(handler_id)
        if signal is not None:
            new_handlers = [
                h for h in self.signal_handlers[signal]
                if h[0] != handler_id
            ]
            self.signal_handlers[signal] = new_handlers

    async def signal_emit(self, signal, *args):
        handlers = self.signal_handlers[signal]
        for handler_id, callback, callback_data in handlers:
            handler_rv = callback(self, signal, *callback_data, *args)
            if inspect.isawaitable(handler_rv):
                handler_rv = await handler_rv
            if handler_rv:
                return


class TaskNibbler:
    class NoData (object):
        pass
    NODATA = NoData()

    def __init__(self):
        self.queue = []
        self.failed = []
        self.task = None
        self.new_work = asyncio.Event()

    async def _task_launcher(self):
        log.debug("[TaskNibbler] launching task")
        try:
            await self._process_queue()
        except Exception as e:
            log.debug(f"[TaskNibbler] Exception {e}")
            log.debug_traceback(e)
        finally:
            self.task = None

    async def _process_queue(self):
        work = []
        retry = []

        while len(self.queue) or len(self.failed):
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
                    if inspect.isawaitable(done):
                        done = await done
                except Exception as e:
                    log.debug("[TaskNibbler] Exception while running", unit)
                    log.debug_traceback(e)

                if not done and retry_count:
                    if isinstance(retry_count, (int, float)):
                        if retry_count > 1:
                            retry_count -= 1
                        else:
                            log.warning("[TaskNibbler] ran out of retries for", unit, data)
                            retry_count = False
                    retry.append((unit, retry_count, data))

            if retry:
                self.failed.append((retry, datetime.utcnow()))
            await asyncio.wait_for(self.new_work.wait(), 1)

    def add_task(self, task, retry, *data):
        self.queue.append((task, retry, data))
        if not self.task:
            self.task = asyncio.create_task(self._task_launcher())
        else:
            self.new_work.set()


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


class AsyncTaskManager:
    def __init__(self):
        self.asyncio_tasks = {}
        self.asyncio_task_last_id = 0
        self.asyncio_loop = asyncio.get_event_loop()
        self.asyncio_thread = threading.get_ident()

    async def _task_wrapper(self, coro, task_id):
        rv = None
        try:
            rv = await coro
        except Exception as e:
            import traceback
            log.error(f"Exception in task: {coro} {e}")
            for ll in traceback.format_exc().split("\n"):
                log.error(ll)
        finally:
            if task_id in self.asyncio_tasks:
                del self.asyncio_tasks[task_id]
        return rv

    def __call__(self, coro):
        """
        self.async_task = AsyncTaskManager()
        self.async_task(coro())
        """

        if inspect.isawaitable(coro):
            current_thread = threading.get_ident()
            task_id = self.asyncio_task_last_id
            self.asyncio_task_last_id += 1

            if current_thread == self.asyncio_thread:
                task = asyncio.create_task(self._task_wrapper(coro, task_id))
            else:
                task = asyncio.run_coroutine_threadsafe(
                    self._task_wrapper(coro, task_id), self.asyncio_loop
                )
            self.asyncio_tasks[task_id] = task
            return task
        else:
            return coro

    async def finish(self):
        tasks = self.asyncio_tasks.values()
        if not tasks:
            return

        done, pending = await asyncio.wait(tasks, timeout=1, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            if task.exception() is not None:
                log.error(f"Task exited with exception: {task} {task.exception()}")
        for task in pending:
            task.cancel()

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
        import shutil
        from mfp import log

        execfile = shutil.which(self.exec_file)
        self.callback = log_monitor
        self.process = await asyncio.create_subprocess_exec(
            execfile, *[str(a) for a in self.exec_args],
            stdin=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )
        self.monitor_task = asyncio.create_task(self.monitor())

    async def monitor(self):
        while True:
            try:
                nextline = await self.process.stdout.readline()
                if not nextline:
                    break

                nextline = nextline.decode().strip()

                cb_return = self.callback(nextline, self.log_module, self.log_raw)
                if inspect.isawaitable(cb_return):
                    await cb_return

            except asyncio.CancelledError:
                break

            except Exception as e:
                print("AsyncExecMonitor: exiting with error", e)
                break

    async def cancel(self):
        try:
            self.monitor_task.cancel()
            self.process.terminate()
            await self.process.wait()
            await self.monitor_task
        except:
            pass
