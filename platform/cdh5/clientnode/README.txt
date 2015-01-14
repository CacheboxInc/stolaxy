Testing a sample Hadoop MR job. Fire up a clientnode
# docker run -t -i -e NAMENODE_HOST=node1.cachebox.com -e NAMENODE_PORT=8022 -e NAMENODE_HTTP_ADDRESS=50070 --net=host clientnode /bin/bash
# su - hdfs
# export HADOOP_HOME=/usr/
# cd /usr/lib/hadoop-0.20-mapreduce/
# hadoop fs -copyFromLocal README.txt /tmp/
# hadoop jar hadoop-examples.jar wordcount hdfs:/tmp/README.txt /tmp/wordcount/
