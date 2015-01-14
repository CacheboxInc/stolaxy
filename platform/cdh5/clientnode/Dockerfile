# docker base image for cdh5. use this and build the namenode and
# datanodes.

# This particular image is setup to run the resource manager and the
#  name node on the same docker instance.

FROM muralinagaraj/cdh5-base
MAINTAINER Murali Nagaraj <murali.nagaraj@cachebox.com>

RUN apt-get update
RUN apt-get install -y --force-yes --no-install-recommends hadoop-client
RUN mkdir -p /cachebox/
ADD conf /cachebox/conf/

ADD gencn.py /cachebox/
ADD start.sh /cachebox/start.sh
ENTRYPOINT ["/cachebox/start.sh"]

CMD ["/bin/bash"]
