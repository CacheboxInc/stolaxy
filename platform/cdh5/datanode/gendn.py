#!/usr/bin/python

import os
import string

namenode_host = os.environ['NAMENODE_HOST']
namenode_port = os.environ['NAMENODE_PORT']
namenode_http_address = os.environ['NAMENODE_HTTP_ADDRESS']

datanode_port = os.environ['DATANODE_PORT']
datanode_http_address = os.environ['DATANODE_HTTP_ADDRESS']
datanode_ipc_address = os.environ['DATANODE_IPC_ADDRESS']

resource_tracker_port = os.environ['RESOURCE_TRACKER_PORT']

config = {
    'datanode_ipc_address':datanode_ipc_address,
    'datanode_http_address':datanode_http_address,
    'datanode_port':datanode_port,
    'namenode_http_address':namenode_http_address,
    'namenode_host':namenode_host,
    'namenode_port':namenode_port,
    'resource_tracker_port':resource_tracker_port
    }

coresite = string.Template(
    open('/cachebox/conf/core-site.xml').read()
    ).substitute(config)
    
open('/etc/hadoop/conf/core-site.xml', 'w').write(coresite)

hdfssite = string.Template(
    open('/cachebox/conf/hdfs-site.xml').read()
    ).substitute(config)
    
open('/etc/hadoop/conf/hdfs-site.xml', 'w').write(hdfssite)
