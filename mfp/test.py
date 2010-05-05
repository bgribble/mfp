
import time

from cp_metro import CPMetro
from cp_print import CPPrint

metro = CPMetro()
pp = CPPrint()

metro.connect(0, pp, 0)

metro.send(250, 1)
metro.send(True, 0)

time.sleep(10)

print "done"
