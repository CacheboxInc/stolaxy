#!/bin/bash

set -e

mkdir -p /data/1/dfs/dn  /data/1/yarn/local /data/1/yarn/logs
chown -R hdfs:hdfs /data/1/dfs/dn
chown -R yarn:yarn /data/1/yarn/local
chown -R yarn:yarn /data/1/yarn/logs

chmod 700 /data/1/dfs/dn

/cachebox/gendn.py

service hadoop-hdfs-datanode start
service hadoop-yarn-nodemanager start

exec "$@"
