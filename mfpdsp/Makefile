
CC=gcc 
CFLAGS=-std=gnu99 -fpic 
PKGCONFPKG="glib-2.0 json-glib-1.0 serd-0"
CFLAGS += $(shell pkg-config --cflags $(PKGCONFPKG))
EXTLIBS := $(shell pkg-config --libs $(PKGCONFPKG)) -ljack -lrt

INSTROOT = ../virtual/
BINFILES = mfpdsp
LIBFILES = libmfpdsp.so

MFPDSP_OBJ=$(shell ls *.c | sed -e 's/.c$$/.o/')

all: libmfpdsp.so mfpdsp

clean:
	rm -f *.o libmfpdsp.so mfpdsp

install: all
	cp -p $(BINFILES) $(INSTROOT)/bin/
	cp -p $(LIBFILES) $(INSTROOT)/lib/

.c.o: mfp_dsp.h builtin.h
	$(CC) $(CFLAGS) -c $? 


libmfpdsp.so: $(MFPDSP_OBJ)
	$(CC) -shared $+ -o $@ $(EXTLIBS)

mfpdsp: libmfpdsp.so main.o 
	$(CC) main.o -o mfpdsp -L . -l mfpdsp 
