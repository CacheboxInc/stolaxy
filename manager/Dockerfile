# 

FROM ubuntu:precise
MAINTAINER Murali Nagaraj <murali.nagaraj@cachebox.com>

RUN mkdir -p /cachebox/stomp
ADD netaddr-0.7.10.tar.gz /cachebox/stomp/
RUN apt-get update
RUN apt-get install -y --force-yes --no-install-recommends python3 python3-sqlalchemy openssh-client
RUN cd /cachebox/stomp/netaddr-0.7.10 && python3 setup.py install

CMD ["/bin/bash"]
