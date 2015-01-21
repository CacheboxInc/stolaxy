# 

FROM ubuntu:precise
MAINTAINER Murali Nagaraj <murali.nagaraj@cachebox.com>

RUN apt-get update
RUN apt-get install -y --force-yes --no-install-recommends python-sqlalchemy openssh-client gcc python-setuptools python-dev
RUN easy_install bitarray

CMD ["/bin/bash"]
