# docker base image for cdh5. use this and build the namenode and
# datanodes.

FROM muralinagaraj/cdh5-base
MAINTAINER Murali Nagaraj <murali.nagaraj@cachebox.com>

RUN apt-get install -y --force-yes --no-install-recommends hadoop-yarn-nodemanager hadoop-hdfs-datanode hadoop-mapreduce

RUN mkdir -p /cachebox/
ADD conf /cachebox/conf/

ADD gendn.py /cachebox/
ADD start.sh /cachebox/start.sh

ENTRYPOINT ["/cachebox/start.sh"]

CMD ["/bin/bash"]
