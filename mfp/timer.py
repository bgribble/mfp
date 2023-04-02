#! /usr/bin/env python
'''
timer.py
Multi-timer implementation
'''

import asyncio
import inspect
from datetime import datetime

from mfp import log

class MultiTimer:
    def __init__(self):
        self.next_id = 0
        self.scheduled = {}

    async def _wait(self, item_id, deadline, callback, data):
        await asyncio.sleep((deadline - datetime.now()).total_seconds())
        cb = callback(*data)
        if inspect.isawaitable(cb):
            await cb
        del self.scheduled[item_id]

    def schedule(self, deadline, callback, data=[]):
        item_id = self.next_id
        self.next_id += 1
        task = asyncio.create_task(
            self._wait(item_id, deadline, callback, data)
        )
        self.scheduled[item_id] = (deadline, task, item_id)
        return item_id

    def cancel(self, item_id):
        if item_id in self.scheduled:
            old_task = self.scheduled[item_id]
            del self.scheduled[item_id]
            old_task.cancel()
