# docker base image for cdh5. use this and build the namenode and
# datanodes. build as docker build -t muralinagaraj/cdh5

FROM ubuntu:precise
MAINTAINER Murali Nagaraj <murali.nagaraj@cachebox.com>

COPY gplextras.list /etc/apt/sources.list.d/gplextras.list
COPY cdh5-repository_1.0_all.deb /
RUN dpkg -i cdh5-repository_1.0_all.deb
RUN apt-get update
RUN apt-get install -y --force-yes --no-install-recommends openjdk-7-jre

CMD ["/bin/bash"]
