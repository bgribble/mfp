import inspect
import io

from ..processor import Processor
from ..mfp_app import MFPApp
from ..bang import Uninit

class EOF:
    pass


class FileIO(Processor):
    doc_tooltip_obj = "File I/O processor"
    doc_tooltip_inlet = ["Message data or method call input"]
    doc_tooltip_outlet = ["File data output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        self.filename = None
        self.fileobj = None
        self.mode = "r"
        self.need_close = True

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        if len(initargs) > 1:
            self.mode = initargs[1]
        if len(initargs) > 0:
            if isinstance(initargs[0], io.IOBase):
                self.fileobj = initargs[0]
                self.filename = self.fileobj.name
                self.mode = self.fileobj.mode
                self.need_close = False
            else:
                self.filename = initargs[0]
                self.open()

    async def trigger(self):
        self.fileobj.write(self.inlets[0])
        self.inlets[0] = Uninit

    async def method(self, message, inlet):
        rv = message.call(self)
        if inspect.isawaitable(rv):
            rv = await rv
        self.inlets[inlet] = Uninit
        self.outlets[0] = rv

    def read(self, size=None):
        if size is None:
            rv = self.fileobj.read()
        else:
            rv = self.fileobj.read(size)
        if rv == '':
            return EOF()
        return rv

    def readline(self):
        rv = self.fileobj.readline()
        if rv == '':
            return EOF()
        return rv

    def readlines(self):
        return self.fileobj.readlines()

    def use(self, fileobj):
        self.fileobj = fileobj
        self.filename = fileobj.name
        self.mode = fileobj.mode

    def open(self, filename=None, mode=None):
        if filename is not None:
            self.filename = filename
        if mode is not None:
            self.mode = mode
        if self.filename is not None:
            if self.fileobj and self.need_close:
                self.close()
            self.fileobj = open(self.filename, self.mode)
            self.need_close = True

    def close(self):
        if self.fileobj:
            self.fileobj.close()
            self.fileobj = None


def register():
    MFPApp().register("file", FileIO)
