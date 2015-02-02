#!/usr/bin/env python3

import datetime
import docker
import getopt
import random
import subprocess
import sys
import threading
import traceback
import uuid

from application import *
from configuration import *
from configdb import *
from group import *
from host import *
from ports import *
from user import *

_local = threading.local()

class Hadoop(Application):
    atype = configuration.application_types.get('HADOOP')

    def create1(self, user, name = None):
        _local.dockerinstances = []
        hosts = Host.listing()
        if hosts.count() == 0:
            print ('not enough physical hosts to launch application!')
            raise

        print ('creating a hadoop - map reduce cluster with %d hosts' % hosts.count())

        hosts = list(hosts)
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

        owner = User.get(user)

        now = datetime.datetime.now()
        application = DBApplication(
            cluster_id = cluster_id,
            name = name,
            vipnetwork = str(vipnetwork),
            created = now,
            modified = now,
            owner = owner.id,
            atype = Hadoop.atype,
            astate = self.application_states.get('POWERED_ON')
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
    
        #print (namenode_launch_cmd)
    
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
            docker_id = docker_id,
            vstate = self.application_states.get('POWERED_ON')
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

            #print(datanode_launch_cmd)

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
                docker_id = docker_id,
                vstate = self.application_states.get('POWERED_ON')
                )

            session.add(vnode)

        return

    def create(self, **args):
        user = args.get('user')
        name = args.get('name')
        try:
            ret = self.create1(user, name)
        except:
            #traceback.print_exc()
            session.rollback()
            for host, instance in _local.dockerinstances:
                docker.cleanup_instance(host, instance)
            return None
        else:
            session.commit()
            return ret

    def get(self, **args):
        application_id = args.get('application_id')
        query = session.query(DBApplication)
        return query.filter(DBApplication.cluster_id == application_id).one()

    def delete(self, **args):
        application_id = args.get('application_id')
        if application_id == None:
            usage()

        app = self.get(application_id = application_id)
        assert app.atype == self.atype

        for node in app.nodes:
            docker.cleanup_instance(node.pipaddress, node.docker_id)
            session.delete(node)

        session.delete(app)
        session.commit()

    def list(self, **args):
        query = session.query(DBApplication)
        applications = query.filter(DBApplication.atype == self.atype)

        if args.get('op') != 'list':
            return applications
            
        # user has requested this listing, pretty print

        if applications.count() > 0:
            print ("{:<32s}{:<16s}{:<16s}{:<16s}{:<8s}{:<32s}".format(
                    "id", "name", "owner", "state", "scale", "created")
                   )
        for app in applications:
            owner = User.get_by_id(app.owner)
            nhosts = len(set([node.pipaddress for node in app.nodes]))
            astate = self.application_states_print.get(app.astate)
            print ("{:<32s}{:<16s}{:<16s}{:<16s}{:<8d}{:<32s}".format(
                    app.cluster_id, app.name, owner.name, astate, nhosts, str(app.created))
                   )

    def stop(self, **args):
        application_id = args.get('application_id')
        if application_id is None:
            usage()

        application = self.get(**args)

        for vnode in application.nodes:
            ret, out, err = docker.docker_cmd(vnode.pipaddress, vnode.docker_id, 'stop')
            if ret != 0:
                print("WARNING: could not stop component %s on %s." % (
                        vnode.docker_id, vnode.pipaddress)
                      )
                continue
            vnode.vstate = self.application_states.get('POWERED_OFF')
            session.add(vnode)
        
        application.astate = self.application_states.get('POWERED_OFF')
        session.add(application)

        session.commit()
        return


    def start(self, **args):
        application_id = args.get('application_id')
        if application_id is None:
            usage()

        application = self.get(**args)

        for vnode in application.nodes:
            ret, out, err = docker.docker_cmd(vnode.pipaddress, vnode.docker_id, 'start')
            if ret != 0:
                print("WARNING: could not start component %s on %s." % (
                        vnode.docker_id, vnode.pipaddress)
                      )
                continue
            vnode.vstate = self.application_states.get('POWERED_ON')
            session.add(vnode)
        
        application.astate = self.application_states.get('POWERED_ON')
        session.add(application)

        session.commit()
        return


    def pause(self, **args):
        application_id = args.get('application_id')
        if application_id is None:
            usage()

        application = self.get(**args)

        for vnode in application.nodes:
            ret, out, err = docker.docker_cmd(vnode.pipaddress, vnode.docker_id, 'pause')
            if ret != 0:
                print("WARNING: could not pause component %s on %s." % (
                        vnode.docker_id, vnode.pipaddress)
                      )
                continue
            vnode.vstate = self.application_states.get('PAUSED')
            session.add(vnode)
        
        application.astate = self.application_states.get('PAUSED')
        session.add(application)

        session.commit()
        return

    def unpause(self, **args):
        application_id = args.get('application_id')
        if application_id is None:
            usage()

        application = self.get(**args)

        for vnode in application.nodes:
            ret, out, err = docker.docker_cmd(vnode.pipaddress, vnode.docker_id, 'unpause')
            if ret != 0:
                print("WARNING: could not unpause component %s on %s." % (
                        vnode.docker_id, vnode.pipaddress)
                      )
                continue
            vnode.vstate = self.application_states.get('POWERED_ON')
            session.add(vnode)
        
        application.astate = self.application_states.get('POWERED_ON')
        session.add(application)

        session.commit()
        return

hadoop = Hadoop()

def usage():
    print ("usage: hadoop.py --create --name=cluster name")
    print ("usage: hadoop.py --delete --application=application_id")
    print ("usage: hadoop.py --start --application=application_id")
    print ("usage: hadoop.py --stop --application=application_id")
    print ("usage: hadoop.py --pause --application=application_id")
    print ("usage: hadoop.py --resume --application=application_id")
    print ("usage: hadoop.py --snapshot --application=application_id")
    print ("usage: hadoop.py --backup --application=application_id")
    print ("usage: hadoop.py --list")
    
    sys.exit(1)

def main():
    ops = []
    name = None
    application = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "", 
                                   hadoop.application_ops + 
                                   ["name=",
                                    "application="
                                    ])
        
    except (getopt.GetoptError, err):
        print (str(err))
        usage()
        sys.exit(2)

    args = {}
    for o, a in opts:
        if o.strip('--') in hadoop.application_ops:
            ops.append(o.strip('--'))
            args['op'] = o.strip('--')
        elif o in ("--name"):
            name = a
            args['name'] = a
            args['user'] = 'administrator'
        elif o in ("--application"):
            application = a
            args['application_id'] = a
        elif o in ("--help"):
            usage()

    if len(ops) > 1 or len(ops) == 0:
        usage()
    
    method = getattr(hadoop, args.get('op'))
    method(**args)
    return

if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        pass
    except:
        print(sys.exc_info()[1])
