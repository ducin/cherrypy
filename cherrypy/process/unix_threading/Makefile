SHELL = /bin/bash

.SUFFIXES:
.SUFFIXES: .c .o

CC = gcc
INCLUDE = /usr/local/include/python2.5
CFLAGS = -fno-strict-aliasing \
	 -Wno-long-double \
	 -no-cpp-precomp \
	 -mno-fused-madd \
	 -DNDEBUG -g -O3 \
	 -Wall -Wstrict-prototypes \
	 -I$(INCLUDE) -pg
COMPILE = $(CC) $(CFLAGS) -c

LD = $(CC)
LDFLAGS = -undefined dynamic_lookup

OBJS = _pthread_cond.o 
LIBRARY = _pthread_cond.so
LIBS = 

all: $(LIBRARY) 

$(LIBRARY): $(OBJS)
	$(LD) $(LDFLAGS) -bundle $(OBJS) $(LIBS) -o $(LIBRARY)

_pthread_cond.o: _pthread_cond.c 
	$(COMPILE) $< -o $@

# for flymake support
check-syntax:
	$(COMPILE) _pthread_cond.c -o /dev/null

clean:
	rm -f $(LIBRARY)
	rm -f $(OBJS)

