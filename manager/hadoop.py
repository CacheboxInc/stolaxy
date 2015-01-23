#!/usr/bin/env python3

import datetime
import docker
import random
import subprocess
import sys
import threading
import traceback
import uuid

from configuration import *
from configdb import *
from host import *
from ports import *

_local = threading.local()

def create_mapreduce1(user, name = None):

    _local.dockerinstances = []
    hosts = Host.getHosts()
    if len(hosts) == 0:
        print ('not enough physical hosts to launch application!')
        raise

    print ('creating a hadoop - map reduce cluster with %d hosts' % len(hosts))

    cluster_id = uuid.uuid4().hex[0:16]
    if name is None:
        name = cluster_id

    namenode_host = random.choice(hosts)
    datanodes = hosts

    config = {}

    namenode_host_ports = Ports(namenode_host.ports)
    namenode_port = namenode_host_ports.assignFreePort()
    namenode_http_address = namenode_host_ports.assignFreePort()
    jobhistory_port = namenode_host_ports.assignFreePort()
    jobhistory_webapp_port = namenode_host_ports.assignFreePort()
    resource_tracker_port = namenode_host_ports.assignFreePort()

    config['namenode'] = {
        'namenode_physical_host':namenode_host.ipaddress,
        'namenode_port':namenode_port,
        'namenode_http_address':namenode_http_address,
        'jobhistory_port':jobhistory_port,
        'jobhistory_webapp_port':jobhistory_webapp_port,
        'resource_tracker_port':resource_tracker_port
        }

    config['datanodes'] = []

    namenode_host.ports = namenode_host_ports.ports

    for datanode in datanodes:
        datanode_host_ports = Ports(datanode.ports)
        datanode_port = datanode_host_ports.assignFreePort()
        datanode_ipc_address = datanode_host_ports.assignFreePort()
        datanode_http_address = datanode_host_ports.assignFreePort()

        config['datanodes'].append({
                'datanode_physical_host':datanode.ipaddress, # physical host
                'datanode_port': datanode_port,
                'datanode_ipc_address':datanode_ipc_address,
                'datanode_http_address':datanode_http_address
                })

        datanode.ports = datanode_host_ports.ports

    vipindex = 1
    vipnetwork = configuration.assignVIPNetwork()

    now = datetime.datetime.now()
    application = DBApplication(
        cluster_id = cluster_id,
        name = name,
        vipnetwork = str(vipnetwork),
        created = now,
        modified = now,
        owner = user
        )
    
    session.add(application)
    session.flush()

    fqdn = '%s.weave.local' % cluster_id
    namenode_fqdn = 'namenode%s.%s' % (vipindex, fqdn)
    namenode_vipaddress = str(vipnetwork[vipindex])
    vipindex += 1

    namenode_launch_cmd = ' '.join((
            "weave run --with-dns",
            '%s/24' % namenode_vipaddress,
            "-ti",
            "-h %s" % namenode_fqdn,
            "-e NAMENODE_HOST=%s" % namenode_fqdn,
            "-e NAMENODE_PORT=%s" % namenode_port,
            "-e NAMENODE_HTTP_ADDRESS=%s" % namenode_http_address,
            "-e JOBHISTORY_PORT=%s" % jobhistory_port,
            "-e JOBHISTORY_WEBAPP_PORT=%s" % jobhistory_webapp_port,
            "-e RESOURCE_TRACKER_PORT=%s" % resource_tracker_port,
            "namenode /bin/bash"
            ))
    
    print ('launching namenode')    
    print (namenode_launch_cmd)
    
    nn = subprocess.Popen(
        (
            "ssh",
            config['namenode']['namenode_physical_host'],
            "%s" % namenode_launch_cmd
            ),
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
        )
    
    out, err = nn.communicate()
    
    if nn.returncode != 0:
        print ('error launching namenode: %s, %s' % (out, err))
        raise

    docker_id = out.decode().strip('\n')
    _local.dockerinstances.append((
            config['namenode']['namenode_physical_host'],
            docker_id))

    vnode = DBVirtualNode(
        created = now,
        modified = now,
        vipaddress = namenode_vipaddress,
        pipaddress = config['namenode']['namenode_physical_host'],
        application_id = application.cluster_id,
        docker_id = docker_id
        )

    session.add(vnode)

    for datanode in config['datanodes']:
        datanode_vipaddress = str(vipnetwork[vipindex])
        datanode_fqdn = 'datanode%s.%s' % (vipindex, fqdn)
        vipindex += 1
        datanode_launch_cmd = ' '.join((
                "weave run --with-dns",
                '%s/24' % datanode_vipaddress,
                "-ti",
                "-h %s" % datanode_fqdn,
                "-e NAMENODE_HOST=%s" % namenode_fqdn,
                "-e NAMENODE_PORT=%s" % namenode_port,
                "-e NAMENODE_HTTP_ADDRESS=%s" % namenode_http_address,
                "-e DATANODE_PORT=%s" % datanode['datanode_port'],
                "-e DATANODE_HTTP_ADDRESS=%s" % datanode['datanode_http_address'],
                "-e DATANODE_IPC_ADDRESS=%s" % datanode['datanode_ipc_address'],
                "-e JOBHISTORY_PORT=%s" % jobhistory_port,
                "-e JOBHISTORY_WEBAPP_PORT=%s" % jobhistory_webapp_port,
                "-e RESOURCE_TRACKER_PORT=%s" % resource_tracker_port,
                "datanode /bin/bash"
                ))

        print ('launching datanode')
        print(datanode_launch_cmd)
        dn = subprocess.Popen(
            (
                "ssh",
                datanode['datanode_physical_host'],
                "%s" % datanode_launch_cmd
                ),
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
            )
    
        out, err = dn.communicate()
    
        if dn.returncode != 0:
            print('error launching datanode: %s %s' % (out ,err))
            raise

        docker_id = out.decode().strip('\n')
        _local.dockerinstances.append((
                datanode['datanode_physical_host'],
                docker_id))

        vnode = DBVirtualNode(
            created = now,
            modified = now,
            vipaddress = datanode_vipaddress,
            pipaddress = datanode['datanode_physical_host'],
            application_id = application.cluster_id,
            docker_id = docker_id
            )

        session.add(vnode)

    return

def create_mapreduce(user, name = None):
    try:
        ret = create_mapreduce1(user, name)
    except:
        traceback.print_exc()
        session.rollback()
        for host, instance in _local.dockerinstances:
            docker.cleanup_instance(host, instance)
    else:
        session.commit()
        return ret
        
if __name__ == '__main__':
    create_mapreduce('jdoe')
    create_mapreduce('jdoe')
