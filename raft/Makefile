all:Raft_pb2.py

Raft_pb2.py: Raft.proto
	protoc -I=. --python_out=. Raft.proto

clean:
	rm -f Raft_pb2.py *.pyc
