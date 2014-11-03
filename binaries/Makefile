all: install

.PHONY: install

ZMQ_LIB = /usr/local/lib
ZMQ_PY = /usr/local/lib/python2.7/dist-packages/

install:
	PWD=`pwd`
	mkdir -p $(ZMQ_LIB) ; \
	cp libzmq.a $(ZMQ_LIB) ; \
	cp libzmq.la $(ZMQ_LIB) ; \
	cd $(ZMQ_LIB) ; \
	ln -s libzmq.so.4.0.0 libzmq.so ; \
	ln -s libzmq.so.4.0.0 libzmq.so.4 ; \
	mkdir -p $(ZMQ_PY) ; \
	cd $(PWD) ; \
	cp -rf zmq $(ZMQ_PY);
