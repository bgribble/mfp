from mfp import log

def _callback_wrapper(self, thunk):
    try:
        return thunk()
    except Exception as e:
        log.debug("Exception in GUI operation:", e)
        log.debug_traceback()
        return False

def clutter_do_later(self, delay, thunk):
    from gi.repository import GObject
    GObject.timeout_add(int(delay), self._callback_wrapper, thunk)

