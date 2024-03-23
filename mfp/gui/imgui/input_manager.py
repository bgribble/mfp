from datetime import datetime, timedelta
import inspect

from mfp import log
from mfp.gui_main import MFPGUI
from ..input_manager import InputManager, InputManagerImpl

from ..event import (
    ButtonPressEvent,
    ButtonReleaseEvent,
    EnterEvent,
    KeyPressEvent,
    KeyReleaseEvent,
    LeaveEvent,
    MotionEvent,
    ScrollEvent
)


class ImguiInputManagerImpl(InputManager, InputManagerImpl):
    backend_name = "imgui"

    async def run_handlers(self, handlers, keysym, coro=None, offset=-1):
        retry_count = 0

        while retry_count < 5:
            try:
                for index, handler in enumerate(handlers):
                    # this is for the case where we were iterating over
                    # handlers and found one async, and are restarting in
                    # the middle of the loop, but async
                    if index < offset:
                        continue
                    elif retry_count == 0 and index == offset:
                        rv = coro
                    else:
                        rv = handler()

                    if inspect.isawaitable(rv):
                        rv = await rv
                    if rv:
                        return True
                return False
            except InputManager.InputNeedsRequeue:
                # handlers might have changed in the previous handler
                handlers = self.get_handlers(keysym)
                retry_count += 1
                offset = -1
            except Exception as e:
                log.error(f"[run_handlers] Exception while handling key command {keysym}: {e}")
                log.debug_traceback()
                return False

    def handle_keysym(self, keysym):
        if not keysym:
            return True
        handlers = self.get_handlers(keysym)
        log.debug(f"[input] keysym={keysym} handlers={handlers}")
        return bool(handlers)

        retry_count = 0
        while retry_count < 5:
            try:
                for item, handler in enumerate(handlers):
                    handler_rv = handler()
                    if inspect.isawaitable(handler_rv):
                        MFPGUI().async_task(self.run_handlers(
                            handlers, keysym, coro=handler_rv, offset=item
                        ))
                        return True
                    if handler_rv:
                        return True
                return False
            except InputManager.InputNeedsRequeue:
                handlers = self.get_handlers(keysym)
                retry_count += 1
            except Exception as e:
                log.error(f"[handle_keysym] Exception while handling key command {keysym}: {e}")
                log.debug_traceback()
                return False
        return False

    def handle_event(self, *args):
        stage, event = args

        keysym = None
        if isinstance(event, (
            KeyPressEvent, KeyReleaseEvent, ButtonPressEvent, ButtonReleaseEvent,
            ScrollEvent
        )):
            try:
                self.keyseq.process(event)
            except Exception as e:
                log.error(f"[handle_event] Exception handling {event}: {e}")
                raise
            if len(self.keyseq.sequences):
                keysym = self.keyseq.pop()

        elif isinstance(event, MotionEvent):
            # FIXME: if the scaling changes so that window.stage_pos would return a
            # different value, that should generate a MOTION event.  Currently we are
            # just kludging pointer_x and pointer_y from the scale callback.
            self.pointer_ev_x = event.x
            self.pointer_ev_y = event.y
            self.pointer_x, self.pointer_y = (
                self.window.screen_to_canvas(event.x, event.y)
            )
            #log.debug(f"[motion] set cursor pos to ({self.pointer_x}, {self.pointer_y})")
            self.keyseq.process(event)
            if len(self.keyseq.sequences):
                keysym = self.keyseq.pop()

        elif isinstance(event, EnterEvent):
            src = event.target
            now = datetime.now()
            if (
                self.pointer_leave_time is not None
                and (now - self.pointer_leave_time) > timedelta(milliseconds=100)
            ):
                self.keyseq.mod_keys = set()
                self.window.grab_focus()
            if (
                src
                and src != self.window
                and self.window.object_visible(src)
            ):
                self.pointer_obj = src
                self.pointer_obj_time = now

        elif isinstance(event, LeaveEvent):
            src = event.target
            self.pointer_leave_time = datetime.now()
            if src == self.pointer_obj:
                self.pointer_lastobj = self.pointer_obj
                self.pointer_obj = None
                self.pointer_obj_time = None
        else:
            return False

        return self.handle_keysym(keysym)
