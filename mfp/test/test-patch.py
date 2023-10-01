
from unittest import IsolatedAsyncioTestCase
from mfp.patch import Patch
from mfp.scope import NaiveScope
from ..mfp_app import MFPApp
from mfp import log, builtins
import simplejson as json
import threading
import asyncio


async def mkproc(case, init_type, init_args=None):
    return await MFPApp().create(init_type, init_args, case.patch, None, init_type)


class PatchTests (IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        MFPApp().no_gui = True
        MFPApp().no_dsp = True
        MFPApp().next_obj_id = 0
        MFPApp().objects = {}
        log.log_quiet = True
        log.log_thread = threading.get_ident()
        log.log_loop = asyncio.get_event_loop()
        await MFPApp().setup()
        builtins.register()
        self.patch = Patch('default', '', None, NaiveScope(), 'default')
        pass

    async def test_loadsave(self):
        o1 = await mkproc(self, "message", "'hello, world'")
        o2 = await mkproc(self, "print")
        await o1.connect(0, o2, 0)

        json_1 = await self.patch.json_serialize()
        await self.patch.delete()

        MFPApp().next_obj_id = 0
        p2 = Patch('default', '', None, NaiveScope(), 'default')
        await p2.json_deserialize(json_1)

        json_2 = await p2.json_serialize()

        dict_1 = json.loads(json_1)
        dict_2 = json.loads(json_2)

        for k in ['export_x', 'export_y', 'export_w', 'export_h',
                  'height', 'width']:
            if k in dict_2['gui_params']:
                del dict_2['gui_params'][k]

        fail = False

        for elt in ['gui_params', 'objects', 'type', 'scopes']:
            if dict_1.get(elt) != dict_2.get(elt):
                print("=======", elt, "========")
                print(dict_1.get(elt))
                print("=====================")
                print(dict_2.get(elt))
                fail = True

        self.assertEqual(fail, False)

    async def test_inlet_outlet(self):
        o1 = await mkproc(self, "inlet")
        o2 = await mkproc(self, "outlet")
        await o1.connect(0, o2, 0)

        p2 = Patch('default', '', None, NaiveScope(), 'default')
        o3 = await MFPApp().create("inlet", None, p2, None, "inlet")
        o4 = await MFPApp().create("outlet", None, p2, None, "outlet")
        await o3.connect(0, o4, 0)

        await self.patch.connect(0, p2, 0)
        await self.patch.send(True)

        self.assertEqual(p2.outlets[0], True)
