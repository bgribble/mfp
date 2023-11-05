from datetime import datetime, timedelta
import inspect

from mfp import log
from mfp.gui_main import MFPGUI
from ..backend_interfaces import InputManagerBackend
from ..input_manager import InputManager

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


class ClutterInputManagerBackend(InputManagerBackend):
    backend_name = "clutter"

    def __init__(self, input_manager):
        self.input_manager = input_manager
        self.event_source_reverse = {}

        super().__init__(input_manager)

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
                handlers = self.input_manager.get_handlers(keysym)
                retry_count += 1
                offset = -1
            except Exception as e:
                log.error(f"[run_handlers] Exception while handling key command {keysym}: {e}")
                log.debug_traceback()
                return False

    def handle_keysym(self, keysym):
        if not keysym:
            return True

        handlers = self.input_manager.get_handlers(keysym)

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
                handlers = self.input_manager.get_handlers(keysym)
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
                self.input_manager.keyseq.process(event)
            except Exception as e:
                log.error(f"[handle_event] Exception handling {event}: {e}")
                raise
            if len(self.input_manager.keyseq.sequences):
                keysym = self.input_manager.keyseq.pop()

        elif isinstance(event, MotionEvent):
            # FIXME: if the scaling changes so that window.stage_pos would return a
            # different value, that should generate a MOTION event.  Currently we are
            # just kludging pointer_x and pointer_y from the scale callback.
            self.input_manager.pointer_ev_x = event.x
            self.input_manager.pointer_ev_y = event.y
            self.input_manager.pointer_x, self.input_manager.pointer_y = (
                self.input_manager.window.backend.screen_to_canvas(event.x, event.y)
            )
            self.input_manager.keyseq.process(event)
            if len(self.input_manager.keyseq.sequences):
                keysym = self.input_manager.keyseq.pop()

        elif isinstance(event, EnterEvent):
            src = event.target

            now = datetime.now()
            if (
                self.input_manager.pointer_leave_time is not None
                and (now - self.input_manager.pointer_leave_time) > timedelta(milliseconds=100)
            ):
                self.input_manager.keyseq.mod_keys = set()
                self.input_manager.window.grab_focus()

            if src and self.input_manager.window.object_visible(src):
                self.input_manager.pointer_obj = src
                self.input_manager.pointer_obj_time = now

        elif isinstance(event, LeaveEvent):
            src = event.target
            self.input_manager.pointer_leave_time = datetime.now()
            if src == self.input_manager.pointer_obj:
                self.input_manager.pointer_lastobj = self.input_manager.pointer_obj
                self.input_manager.pointer_obj = None
                self.input_manager.pointer_obj_time = None
        else:
            return False

        return self.handle_keysym(keysym)
