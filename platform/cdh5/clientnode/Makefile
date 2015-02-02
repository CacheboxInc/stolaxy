.PHONY: clientnode

all:clientnode

clientnode: Dockerfile gencn.py start.sh conf/core-site.xml conf/hdfs-site.xml
	docker build -t clientnode .

clean:
	rm -f *.pyc *.o *~
