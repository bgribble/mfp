
import sys
import _testext

def main():
	libname = sys.argv[1]
	funcname = sys.argv[2]
	setup = sys.argv[3]
	teardown = sys.argv[4]

	rv = _testext.run_dl_test(libname, funcname, setup, teardown)

	if rv is True:
		sys.exit(0)
	elif rv is False:
		sys.exit(1)
	elif rv is None:
		sys.exit(2)

