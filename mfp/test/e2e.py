

from unittest import TestCase 
from subprocess import Popen, PIPE

class e2eIntegration(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def get_output(self, objname, inputs):
        pout, perr = Popen(['mfp', '-b', '-e', objname], 
                           stdin=PIPE, stdout=PIPE).communicate(inputs)
        return pout.split('\n')[:-1]

    def e2e_echo(self):
        out = self.get_output("echo", '1\n2\n3')
        self.assertEqual(out, ['1', '2', '3'])




