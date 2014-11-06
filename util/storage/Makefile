.PHONY: install

all: cbperf install

cbperf: cbperf.c
	gcc -o cbperf cbperf.c -lrt

clean:
	rm -f *.pyc *.o cbperf

install: cbperf
	cp cbperf /usr/bin
