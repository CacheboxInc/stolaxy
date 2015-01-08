# docker base image for cdh5. use this and build the namenode and
# datanodes.

FROM muralinagaraj/cdh5-base
MAINTAINER Murali Nagaraj <murali.nagaraj@cachebox.com>

RUN apt-get install -y --force-yes --no-install-recommends hadoop-yarn-resourcemanager hadoop-hdfs-namenode hadoop-mapreduce-historyserver hadoop-yarn-proxyserver

RUN mkdir -p /cachebox/
ADD conf /cachebox/conf/

ADD gennn.py /cachebox/
ADD start.sh /cachebox/start.sh
ENTRYPOINT ["/cachebox/start.sh"]

CMD ["/bin/bash"]
