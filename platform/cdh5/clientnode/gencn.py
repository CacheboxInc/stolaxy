#!/usr/bin/python

import os
import string

namenode_host = os.environ['NAMENODE_HOST']
namenode_port = os.environ['NAMENODE_PORT']
namenode_http_address = os.environ['NAMENODE_HTTP_ADDRESS']

config = {
    'namenode_http_address':namenode_http_address,
    'namenode_host':namenode_host,
    'namenode_port':namenode_port,
    }

coresite = string.Template(
    open('/cachebox/conf/core-site.xml').read()
    ).substitute(config)
    
open('/etc/hadoop/conf/core-site.xml', 'w').write(coresite)

hdfssite = string.Template(
    open('/cachebox/conf/hdfs-site.xml').read()
    ).substitute(config)
    
open('/etc/hadoop/conf/hdfs-site.xml', 'w').write(hdfssite)
