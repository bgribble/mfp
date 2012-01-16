#
# pyliblo - Python bindings for the liblo OSC library
#
# Copyright (C) 2007-2011  Dominic Sacré  <dominic.sacre@gmx.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of the
# License, or (at your option) any later version.
#

__version__ = '0.9.1'


from cpython cimport PY_VERSION_HEX
cdef extern from 'Python.h':
    void PyEval_InitThreads()

from libc.stdlib cimport malloc, free
cdef extern from 'math.h':
    double modf(double x, double *iptr)

from liblo cimport *

import inspect as _inspect
import weakref as _weakref


class _weakref_method:
    """
    Weak reference to a bound method.
    """
    def __init__(self, f):
        if PY_VERSION_HEX >= 0x03000000:
            self.func = f.__func__
            self.obj = _weakref.ref(f.__self__)
        else:
            self.func = f.im_func
            self.obj = _weakref.ref(f.im_self)
    def __call__(self):
        return self.func.__get__(self.obj(), self.obj().__class__)


class struct:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


cdef str _decode(s):
    # convert to standard string type, depending on python version
    if PY_VERSION_HEX >= 0x03000000 and isinstance(s, bytes):
        return s.decode()
    else:
        return s

cdef bytes _encode(s):
    # convert unicode to bytestring
    if isinstance(s, unicode):
        return s.encode()
    else:
        return s


# forward declarations
cdef class _ServerBase
cdef class Address
cdef class Message
cdef class Bundle


# liblo protocol constants
UDP  = LO_UDP
TCP  = LO_TCP
UNIX = LO_UNIX


################################################################################
#  timetag
################################################################################

cdef lo_timetag _double_to_timetag(double f):
    cdef lo_timetag tt
    cdef double intr, frac
    frac = modf(f, &intr)
    tt.sec = <uint32_t>intr
    tt.frac = <uint32_t>(frac * 4294967296.0)
    return tt

cdef double _timetag_to_double(lo_timetag tt):
    return <double>tt.sec + (<double>(tt.frac) / 4294967296.0)

def time():
    """
    time()

    Returns the current time as a float in OSC format, that is, the number of
    seconds since the epoch (January 1, 1900).
    """
    cdef lo_timetag tt
    lo_timetag_now(&tt)
    return _timetag_to_double(tt)


################################################################################
#  send
################################################################################

cdef _send(target, _ServerBase src, args):
    cdef lo_server from_server
    cdef Address target_address
    cdef int r

    # convert target to Address object, if necessary
    if isinstance(target, Address):
        target_address = target
    elif isinstance(target, tuple):
        # unpack tuple
        target_address = Address(*target)
    else:
        target_address = Address(target)

    # 'from' parameter is NULL if no server was specified
    from_server = src._server if src else NULL

    if isinstance(args[0], (Message, Bundle)):
        # args is already a list of Messages/Bundles
        packets = args
    else:
        # make a single Message from all arguments
        packets = [Message(*args)]

    # send all packets
    for p in packets:
        if isinstance(p, Message):
            message = <Message> p
            r = lo_send_message_from(target_address._address,
                                     from_server,
                                     message._path,
                                     message._message)
        else:
            bundle = <Bundle> p
            r = lo_send_bundle_from(target_address._address,
                                    from_server,
                                    bundle._bundle)

        if r == -1:
            raise IOError("sending failed: %s" %
                          <char*>lo_address_errstr(target_address._address))


def send(target, *args):
    """
    send(target, message)
    send(target, bundle)
    send(target, path[, arg, ...])

    Sends a message or bundle to the the given target, without requiring a
    server.  target may be an Address object, a port number, a (hostname, port)
    tuple, or a URL.
    Exceptions: AddressError, IOError
    """
    _send(target, None, args)


################################################################################
#  Server
################################################################################

class ServerError(Exception):
    """
    Exception raised when creating a liblo OSC server fails.
    """
    def __init__(self, num, msg, where):
        self.num = num
        self.msg = msg
        self.where = where
    def __str__(self):
        s = "server error %d" % self.num
        if self.where: s += " in %s" % self.where
        s += ": %s" % self.msg
        return s


cdef int _callback(const_char *path, const_char *types, lo_arg **argv, int argc,
                   lo_message msg, void *cb_data) with gil:
    cdef int i
    cdef char t
    cdef unsigned char *ptr
    cdef uint32_t size, j

    args = []

    for i from 0 <= i < argc:
        t = types[i]
        if   t == 'i': v = argv[i].i
        elif t == 'h': v = argv[i].h
        elif t == 'f': v = argv[i].f
        elif t == 'd': v = argv[i].d
        elif t == 'c': v = chr(argv[i].c)
        elif t == 's': v = _decode(&argv[i].s)
        elif t == 'S': v = _decode(&argv[i].s)
        elif t == 'T': v = True
        elif t == 'F': v = False
        elif t == 'N': v = None
        elif t == 'I': v = float('inf')
        elif t == 'm': v = (argv[i].m[0], argv[i].m[1], argv[i].m[2], argv[i].m[3])
        elif t == 't': v = _timetag_to_double(argv[i].t)
        elif t == 'b':
            if PY_VERSION_HEX >= 0x03000000:
                v = bytes(<unsigned char*>lo_blob_dataptr(argv[i]))
            else:
                # convert binary data to python list
                v = []
                ptr = <unsigned char*>lo_blob_dataptr(argv[i])
                size = lo_blob_datasize(argv[i])
                for j from 0 <= j < size:
                    v.append(ptr[j])
        else:
            v = None  # unhandled data type

        args.append(v)

    cdef char *url = lo_address_get_url(lo_message_get_source(msg))
    src = Address(url)
    free(url)

    cb = <object>cb_data

    if isinstance(cb.func, _weakref_method):
        func = cb.func()
    else:
        func = cb.func

    func_args = (_decode(<char*>path),
                 args,
                 _decode(<char*>types),
                 src,
                 cb.user_data)

    # call function
    if _inspect.getargspec(func)[1] == None:
        # determine number of arguments to call the function with
        n = len(_inspect.getargspec(func)[0])
        if _inspect.ismethod(func):
            n -= 1  # self doesn't count
        r = func(*func_args[0:n])
    else:
        # function has argument list, pass all arguments
        r = func(*func_args)

    if r == None:
        return 0
    else:
        return r


cdef void _err_handler(int num, const_char *msg, const_char *where) with gil:
    # can't raise exception in cdef callback function, so use a global variable
    # instead
    global __exception
    __exception = ServerError(num, <char*>msg, None)
    if where: __exception.where = <char*>where


# decorator to register callbacks

class make_method:
    """
    @make_method(path, typespec[, user_data])

    Decorator that basically serves the same purpose as add_method().  Note that
    @make_method is defined at module scope, and not a member of class Server.
    """
    # counter to keep track of the order in which the callback functions where
    # defined
    _counter = 0

    def __init__(self, path, types, user_data=None):
        self.spec = struct(counter=make_method._counter,
                           path=path,
                           types=types,
                           user_data=user_data)
        make_method._counter += 1

    def __call__(self, f):
        # we can't access the Server object here, because at the time the
        # decorator is run it doesn't even exist yet, so we store the
        # path/typespec in the function object instead...
        if not hasattr(f, '_method_spec'):
            f._method_spec = []
        f._method_spec.append(self.spec)
        return f


# common base class for both Server and ServerThread

cdef class _ServerBase:
    cdef lo_server _server
    cdef list _keep_refs

    def __init__(self, **kwargs):
        self._keep_refs = []

        if 'reg_methods' not in kwargs or kwargs['reg_methods']:
            self.register_methods()

    def register_methods(self, obj=None):
        """
        register_methods([obj])

        Calls add_method() for all methods of obj decorated with @make_method.
        obj defaults to the Server object itself.  This function is called
        automatically by the Server's init function, unless its reg_methods
        parameter is False.
        """
        if obj == None:
            obj = self
        # find and register methods that were defined using decorators
        methods = []
        for m in _inspect.getmembers(obj):
            if hasattr(m[1], '_method_spec'):
                for spec in m[1]._method_spec:
                    methods.append(struct(spec=spec, name=m[1]))
        # sort by counter
        methods.sort(key=lambda x: x.spec.counter)
        for e in methods:
            self.add_method(e.spec.path, e.spec.types, e.name, e.spec.user_data)

    def get_url(self):
        cdef char *tmp = lo_server_get_url(self._server)
        cdef object r = tmp
        free(tmp)
        return _decode(r)

    def get_port(self):
        return lo_server_get_port(self._server)

    def get_protocol(self):
        return lo_server_get_protocol(self._server)

    def fileno(self):
        """
        fileno()

        Returns the file descriptor of the server socket, or -1 if not supported
        by the underlying server protocol.
        """
        return lo_server_get_socket_fd(self._server)

    def add_method(self, path, typespec, func, user_data=None):
        """
        add_method(path, typespec, callback_func[, user_data])

        Registers a callback function for OSC messages with matching path and
        argument types.  For both path and typespec, None may be used as a
        wildcard.  The optional user_data will be passed on to the callback
        function.  callback_func may be a global function or a class method,
        pyliblo will know what to do either way.
        """
        cdef char *p
        cdef char *t

        if isinstance(path, (bytes, unicode)):
            s = _encode(path)
            p = s
        elif path == None:
            p = NULL
        else:
            raise TypeError("path must be a string or None")

        if isinstance(typespec, (bytes, unicode)):
            s2 = _encode(typespec)
            t = s2
        elif typespec == None:
            t = NULL
        else:
            raise TypeError("typespec must be a string or None")

        # use a weak reference if func is a method, to avoid circular references
        # in cases where func is a method an object that also has a reference to
        # the server (e.g. when deriving from the Server class)
        if _inspect.ismethod(func):
            func = _weakref_method(func)

        cb = struct(func=func, user_data=user_data)
        self._keep_refs.append(cb)
        lo_server_add_method(self._server, p, t, _callback, <void*>cb)

    def send(self, target, *args):
        """
        send(target, message)
        send(target, bundle)
        send(target, path[, arg, ...])

        Sends a message or bundle from this server to the the given target.
        target may be an Address object, a port number, a (hostname, port)
        tuple, or a URL.
        Exceptions: AddressError, IOError
        """
        _send(target, self, args)

    property url:
        """
        The server's URL.
        """
        def __get__(self):
            return self.get_url()

    property port:
        """
        The server's port number.
        """
        def __get__(self):
            return self.get_port()

    property protocol:
        """
        The server's protocol (one of the constants UDP, TCP, UNIX).
        """
        def __get__(self):
            return self.get_protocol()


cdef class Server(_ServerBase):
    """
    Server([port[, proto[, **kwargs]]])

    Creates a new Server object, which can receive OSC messages.  port may be a
    decimal port number or a UNIX socket path.  If omitted, an arbitrary free
    UDP port will be used.  proto can be one of the constants UDP, TCP, UNIX.
    Optional keyword arguments:
    reg_methods: False if you don't want the init function to automatically
                 register callbacks defined with the @make_method decorator.
    Exceptions: ServerError
    """
    def __init__(self, port=None, proto=LO_DEFAULT, **kwargs):
        cdef char *cs

        if port != None:
            p = _encode(str(port));
            cs = p
        else:
            cs = NULL

        global __exception
        __exception = None
        self._server = lo_server_new_with_proto(cs, proto, _err_handler)
        if __exception:
            raise __exception

        _ServerBase.__init__(self, **kwargs)

    def __dealloc__(self):
        self.free()

    def free(self):
        """
        free()

        Frees the underlying server object and closes its port.  Note that this
        will also happen automatically when the server is garbage-collected.
        """
        if self._server:
            lo_server_free(self._server)
            self._server = NULL

    def recv(self, timeout=None):
        """
        recv([timeout])

        Receives and dispatches one OSC message.  Blocking by default, unless
        timeout (in ms) is specified.  timeout may be 0, in which case recv()
        returns immediately.  Returns True if a message was received, False
        otherwise.
        """
        cdef int t, r
        if timeout != None:
            t = timeout
            with nogil:
                r = lo_server_recv_noblock(self._server, t)
            return r and True or False
        else:
            with nogil:
                lo_server_recv(self._server)
            return True


cdef class ServerThread(_ServerBase):
    """
    ServerThread([port[, proto[, **kwargs]]])

    Creates a new ServerThread object, which can receive OSC messages.  Unlike
    Server, ServerThread uses its own thread which runs in the background to
    dispatch messages.  Note that callback methods will not be run in the main
    Python thread!
    port may be a decimal port number or a UNIX socket path. If omitted, an
    arbitrary free UDP port will be used.  proto can be one of the constants
    UDP, TCP, UNIX.
    Optional keyword arguments:
    reg_methods: False if you don't want the init function to automatically
                 register callbacks defined with the @make_method decorator.
    Exceptions: ServerError
    """
    cdef lo_server_thread _server_thread

    def __init__(self, port=None, proto=LO_DEFAULT, **kwargs):
        cdef char *cs

        if port != None:
            p = _encode(str(port));
            cs = p
        else:
            cs = NULL

        # make sure python can handle threading
        PyEval_InitThreads()

        global __exception
        __exception = None
        self._server_thread = lo_server_thread_new_with_proto(cs, proto, _err_handler)
        if __exception:
            raise __exception
        self._server = lo_server_thread_get_server(self._server_thread)

        _ServerBase.__init__(self, **kwargs)

    def __dealloc__(self):
        self.free()

    def free(self):
        """
        free()

        Frees the underlying server object and closes its port.  Note that this
        will also happen automatically when the server is garbage-collected.
        """
        if self._server_thread:
            lo_server_thread_free(self._server_thread)
            self._server_thread = NULL
            self._server = NULL

    def start(self):
        """
        start()

        Starts the server thread, liblo will now start to dispatch any messages
        it receives.
        """
        lo_server_thread_start(self._server_thread)

    def stop(self):
        """
        stop()

        Stops the server thread.
        """
        lo_server_thread_stop(self._server_thread)


################################################################################
#  Address
################################################################################

class AddressError(Exception):
    """
    Exception raised when trying to create an invalid Address object.
    """
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return "address error: %s" % self.msg


cdef class Address:
    """
    Address(hostname, port[, proto])
    Address(port)
    Address(url)

    Creates a new Address object from the given hostname/port or URL.
    proto can be one of the constants UDP, TCP, UNIX.
    Exceptions: AddressError
    """
    cdef lo_address _address

    def __init__(self, addr, addr2=None, proto=LO_UDP):
        if addr2:
            # Address(host, port[, proto])
            s = _encode(addr)
            s2 = _encode(str(addr2))
            self._address = lo_address_new_with_proto(proto, s, s2)
            if not self._address:
                raise AddressError("invalid protocol")
        elif isinstance(addr, int) or (isinstance(addr, str) and addr.isdigit()):
            # Address(port)
            s = str(addr).encode()
            self._address = lo_address_new(NULL, s)
        else:
            # Address(url)
            s = _encode(addr)
            self._address = lo_address_new_from_url(s)
            # lo_address_errno() is of no use if self._addr == NULL
            if not self._address:
                raise AddressError("invalid URL '%s'" % str(addr))

    def __dealloc__(self):
        lo_address_free(self._address)

    def get_url(self):
        cdef char *tmp = lo_address_get_url(self._address)
        cdef object r = tmp
        free(tmp)
        return _decode(r)

    def get_hostname(self):
        return _decode(lo_address_get_hostname(self._address))

    def get_port(self):
        cdef bytes s = lo_address_get_port(self._address)
        if s.isdigit():
            return int(s)
        else:
            return _decode(s)

    def get_protocol(self):
        return lo_address_get_protocol(self._address)

    property url:
        """
        The address' URL.
        """
        def __get__(self):
            return self.get_url()

    property hostname:
        """
        The address' hostname.
        """
        def __get__(self):
            return self.get_hostname()

    property port:
        """
        The address' port number.
        """
        def __get__(self):
            return self.get_port()

    property protocol:
        """
        The address' protocol (one of the constants UDP, TCP, UNIX).
        """
        def __get__(self):
            return self.get_protocol()


################################################################################
#  Message
################################################################################

cdef class _Blob:
    cdef lo_blob _blob

    def __init__(self, arr):
        # arr can by any sequence type
        cdef unsigned char *p
        cdef uint32_t size, i
        size = len(arr)
        if size < 1:
            raise ValueError("blob is empty")
        # copy each element of arr to a C array
        p = <unsigned char*>malloc(size)
        try:
            if isinstance(arr[0], (str, unicode)):
                # use ord() if arr is a string (but not bytes)
                for i from 0 <= i < size:
                    p[i] = ord(arr[i])
            else:
                for i from 0 <= i < size:
                    p[i] = arr[i]
            # build blob
            self._blob = lo_blob_new(size, p)
        finally:
            free(p)

    def __dealloc__(self):
        lo_blob_free(self._blob)


cdef class Message:
    """
    Message(path[, arg, ...])

    Creates a new Message object.
    """
    cdef bytes _path
    cdef lo_message _message
    cdef list _keep_refs

    def __init__(self, path, *args):
        self._keep_refs = []
        # encode path to bytestring if necessary
        self._path = _encode(path)
        self._message = lo_message_new()

        self.add(*args)

    def __dealloc__(self):
        lo_message_free(self._message)

    def add(self, *args):
        """
        add(arg[, ...])

        Appends the given argument(s) to the message.
        """
        for arg in args:
            if (isinstance(arg, tuple) and len(arg) <= 2 and
                    isinstance(arg[0], (bytes, unicode)) and len(arg[0]) == 1):
                # type explicitly specified
                if len(arg) == 2:
                    self._add(arg[0], arg[1])
                else:
                    self._add(arg[0], None)
            else:
                # detect type automatically
                self._add_auto(arg)

    cdef _add(self, type, value):
        cdef uint8_t midi[4]

        # accept both bytes and unicode as type specifier
        cdef char t = ord(_decode(type)[0])

        if t == 'i':
            lo_message_add_int32(self._message, int(value))
        elif t == 'h':
            lo_message_add_int64(self._message, long(value))
        elif t == 'f':
            lo_message_add_float(self._message, float(value))
        elif t == 'd':
            lo_message_add_double(self._message, float(value))
        elif t == 'c':
            lo_message_add_char(self._message, ord(value))
        elif t == 's':
            s = _encode(value)
            lo_message_add_string(self._message, s)
        elif t == 'S':
            s = _encode(value)
            lo_message_add_symbol(self._message, s)
        elif t == 'T':
            lo_message_add_true(self._message)
        elif t == 'F':
            lo_message_add_false(self._message)
        elif t == 'N':
            lo_message_add_nil(self._message)
        elif t == 'I':
            lo_message_add_infinitum(self._message)
        elif t == 'm':
            for n from 0 <= n < 4:
                midi[n] = value[n]
            lo_message_add_midi(self._message, midi)
        elif t == 't':
            lo_message_add_timetag(self._message, _double_to_timetag(value))
        elif t == 'b':
            b = _Blob(value)
            # make sure the blob is not deleted as long as this message exists
            self._keep_refs.append(b)
            lo_message_add_blob(self._message, (<_Blob>b)._blob)
        else:
            raise TypeError("unknown OSC data type '%c'" % t)

    cdef _add_auto(self, value):
        # bool is a subclass of int, so check those first
        if value is True:
            lo_message_add_true(self._message)
        elif value is False:
            lo_message_add_false(self._message)
        elif isinstance(value, int):
            lo_message_add_int32(self._message, int(value))
        elif isinstance(value, long):
            lo_message_add_int64(self._message, long(value))
        elif isinstance(value, float):
            lo_message_add_float(self._message, float(value))
        elif isinstance(value, (bytes, unicode)):
            s = _encode(value)
            lo_message_add_string(self._message, s)
        elif value == None:
            lo_message_add_nil(self._message)
        elif value == float('inf'):
            lo_message_add_infinitum(self._message)
        else:
            # last chance: could be a blob
            try:
                iter(value)
            except TypeError:
                raise TypeError("unsupported message argument type")
            self._add('b', value)


################################################################################
#  Bundle
################################################################################

cdef class Bundle:
    """
    Bundle([timetag, ][message, ...])

    Creates a new Bundle object.  You can optionally specify a time at which the
    messages should be dispatched (as an OSC timetag float), and any number of
    messages to be included in the bundle.
    """
    cdef lo_bundle _bundle
    cdef list _keep_refs

    def __init__(self, *messages):
        cdef lo_timetag tt
        tt.sec, tt.frac = 0, 0
        self._keep_refs = []

        if len(messages) and not isinstance(messages[0], Message):
            t = messages[0]
            if isinstance(t, (float, int, long)):
                tt = _double_to_timetag(t)
            elif isinstance(t, tuple) and len(t) == 2:
                tt.sec, tt.frac = t
            else:
                raise TypeError("invalid timetag")
            # first argument was timetag, so continue with second
            messages = messages[1:]

        self._bundle = lo_bundle_new(tt)
        if len(messages):
            self.add(*messages)

    def __dealloc__(self):
        lo_bundle_free(self._bundle)

    def add(self, *args):
        """
        add(message[, ...])
        add(path[, arg, ...])

        Adds one or more messages to the bundle.
        """
        if isinstance(args[0], Message):
            # args is already a list of Messages
            messages = args
        else:
            # make a single Message from all arguments
            messages = [Message(*args)]

        # add all messages
        for m in messages:
            self._keep_refs.append(m)
            message = <Message> m
            lo_bundle_add_message(self._bundle, message._path, message._message)
