

MFP_CFLAGS=-I ../../mfpdsp -DMFP_USE_SSE 
GLIB_CFLAGS=$(shell pkg-config --cflags glib-2.0)

CFLAGS=${MFP_CFLAGS} ${GLIB_CFLAGS} 

all: extension_1.so

extension_1.so: extension_1.c
	gcc -shared -fPIC ${CFLAGS} -o extension_1.so extension_1.c


