#!/usr/bin/python

import os
import string

jobhistory_port = os.environ['JOBHISTORY_PORT']
jobhistory_webapp_port = os.environ['JOBHISTORY_WEBAPP_PORT']

namenode_host = os.environ['NAMENODE_HOST']
namenode_port = os.environ['NAMENODE_PORT']
namenode_http_address = os.environ['NAMENODE_HTTP_ADDRESS']

resource_tracker_port = os.environ['RESOURCE_TRACKER_PORT']

config = {
    'jobhistory_port':jobhistory_port,
    'jobhistory_webapp_port':jobhistory_webapp_port,
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

yarnsite = string.Template(
    open('/cachebox/conf/yarn-site.xml').read()
    ).substitute(config)
    
open('/etc/hadoop/conf/yarn-site.xml', 'w').write(yarnsite)

mapred = string.Template(
    open('/cachebox/conf/mapred-site.xml').read()
    ).substitute(config)
    
open('/etc/hadoop/conf/mapred-site.xml', 'w').write(mapred)

