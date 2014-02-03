
CC=gcc 
CFLAGS=-std=gnu99 -fpic 
PKGCONFPKG="glib-2.0 json-glib-1.0 serd-0"
CFLAGS += $(shell pkg-config --cflags $(PKGCONFPKG))
EXTLIBS := $(shell pkg-config --libs $(PKGCONFPKG)) -ljack -lrt

MFPDSP_OBJ=$(shell ls *.c | sed -e 's/.c$$/.o/')

all: mfpdsp.so

.c.o: mfp_dsp.h builtin.h
	$(CC) $(CFLAGS) -c $? 


mfpdsp.so: $(MFPDSP_OBJ)
	$(CC) -shared $+ -o $@ $(EXTLIBS)
