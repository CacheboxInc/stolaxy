#!/bin/bash

set -e

mkdir -p /data/1/dfs/nn /data/1/yarn/local /data/1/yarn/logs
chown -R hdfs:hdfs /data/1/dfs/nn
chown -R yarn:yarn /data/1/yarn/local
chown -R yarn:yarn /data/1/yarn/logs

chmod 700 /data/1/dfs/nn
python /cachebox/gennn.py

su -l hdfs -c "hdfs namenode -format"

service hadoop-hdfs-namenode start
service hadoop-mapreduce-historyserver start
# service hadoop-yarn-proxyserver start
service hadoop-yarn-resourcemanager start

su -l hdfs -c "hadoop fs -mkdir /tmp"
su -l hdfs -c "hadoop fs -chmod -R 1777 /tmp"
su -l hdfs -c "hadoop fs -mkdir -p /user/history"
su -l hdfs -c "hadoop fs -chmod -R 1777 /user/history"
su -l hdfs -c "hadoop fs -chown mapred:hadoop /user/history"

exec "$@"
