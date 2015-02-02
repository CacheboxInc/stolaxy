#!/bin/bash

set -e

export HADOOP_HOME=/usr/

python /cachebox/gencn.py

exec "$@"
