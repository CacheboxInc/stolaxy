#!/bin/bash

set -e

mkdir -p /data/1/dfs/dn
chown -R hdfs:hdfs /data/1/dfs/dn
chmod 700 /data/1/dfs/dn

/cachebox/gendn.py

for x in `cd /etc/init.d ; ls hadoop-hdfs-*` ; do service $x start ; done

exec "$@"
