


MFP_LIBDIR=../../build/lib.linux-x86_64-2.7
MFP_CFLAGS=-I ../../mfpdsp -DMFP_USE_SSE 
MFP_LDFLAGS=-L$(MFP_LIBDIR) -lmfpdsp 

GLIB_CFLAGS=$(shell pkg-config --cflags glib-2.0)
GLIB_LDFLAGS=$(shell pkg-config --libs glib-2.0)
CFLAGS=${MFP_CFLAGS} ${GLIB_CFLAGS} 

all: extension_1.so

extension_1.so: extension_1.c
	gcc -shared -fPIC ${CFLAGS} -o extension_1.so extension_1.c


