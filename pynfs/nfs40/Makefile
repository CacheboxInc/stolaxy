.PHONY: build

all: build nfs_pb2.py

build:
	python setup.py build

nfs_pb2.py: nfs.proto
	protoc -I=. --python_out=. nfs.proto

clean:
	rm -f *.o *.pyc *.log

