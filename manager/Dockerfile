# 

FROM ubuntu:precise
MAINTAINER Murali Nagaraj <murali.nagaraj@cachebox.com>

RUN apt-get update
RUN apt-get install -y --force-yes --no-install-recommends python3 python3-sqlalchemy openssh-client openssh-server
RUN mkdir /var/run/sshd
RUN echo 'root:screencast' | chpasswd
RUN sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

EXPOSE 22

RUN mkdir -p /cachebox/stomp
ADD netaddr-0.7.10.tar.gz /cachebox/stomp/
RUN cd /cachebox/stomp/netaddr-0.7.10 && python3 setup.py install

CMD ["/usr/sbin/sshd", "-D"]
#CMD ["/bin/bash"]
