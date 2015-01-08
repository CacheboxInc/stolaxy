.PHONY: datanode

all:datanode

datanode: Dockerfile gendn.py start.sh conf/core-site.xml conf/hdfs-site.xml
	docker build -t namenode .

clean:
	rm -f *.pyc *.o *~
