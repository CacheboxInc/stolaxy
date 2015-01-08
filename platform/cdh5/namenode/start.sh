#!/bin/bash

set -e

mkdir -p /data/1/dfs/nn
chown -R hdfs:hdfs /data/1/dfs/nn
chmod 700 /data/1/dfs/nn
python /cachebox/gennn.py

su -l hdfs -c "hdfs namenode -format"

for x in `cd /etc/init.d ; ls hadoop-hdfs-*` ; do service $x start ; done
su -l hdfs -c "hadoop fs -mkdir /tmp"
su -l hdfs -c "hadoop fs -chmod -R 1777 /tmp"

exec "$@"
