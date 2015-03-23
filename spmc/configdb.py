#!/usr/bin/env python3

import os
import sys

from sqlalchemy import Binary, Column, ForeignKey, Integer, String, DateTime, SmallInteger
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

CONFIG_DB = 'sqlite:////tmp/config.db'
 
Base = declarative_base()
 
class DBConfiguration(Base):
    __tablename__ = 'configuration'
    id = Column(Integer, primary_key = True)
    vipaddresses = Column(Binary)
    vipallocate = Column(String)

    def to_dict(self):
        return {
            'id': self.id,
            'vipallocate': self.vipallocate
        }


    def __repr__(self):
        return """
DBConfiguration:
id %s
vipallocate %s
""" % (
            self.id,
            self.vipallocate
            )

class DBGroup(Base):
    __tablename__ = 'group'
    id = Column(Integer, primary_key = True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    name = Column(String, unique = True)
    users = relationship("DBUser", backref="group")

    def to_dict(self):
        users = []
        for user in self.users:
            if user.role != 'admin':
                users.append(user.to_dict())

        return {
            'id': self.id,
            'created': str(self.created),
            'modified': str(self.modified),
            'name': self.name,
            'users': users
        }

    def __repr__(self):
        return """
DBGroup:
id %s
created %s
modified %s
name %s
users %s
""" % (
            self.id,
            self.created,
            self.modified,
            self.name,
            self.users
            )

class DBUser(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key = True)
    created = Column(DateTime, nullable = False)
    modified = Column(DateTime, nullable = False)
    username = Column(String, unique = True)
    password = Column(String, nullable = False)
    fullname = Column(String, nullable = True)
    email = Column(String, unique = True)
    group_id = Column(Integer, ForeignKey('group.id'))
    role = Column(String, nullable=False)
    firstlogin = Column(DateTime, nullable=True)
    lastlogin = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    online = Column(SmallInteger, default=0)

    def to_dict(self):
        if self.group_id:
            query = session.query(DBGroup)
            group = query.filter(DBGroup.id == self.group_id).one()
            group_dict = {'id': group.id, 'name': group.name}
        else:
            group_dict = self.group_id

        return {
            'id': self.id,
            'created': str(self.created),
            'modified': str(self.modified),
            'username': self.username,
            'group': group_dict,
            'role': self.role,
            'email': self.email,
            'fullname': self.fullname,
            'firstlogin': str(self.firstlogin),
            'lastlogin': str(self.lastlogin),
            'online': self.online,
            'login_count': self.login_count
        }

    def __repr__(self):
        return """
DBUser:
id %s
created %s
modified %s
username %s
group %s
role %s
email %s
fullname %s
firstlogin %s
lastlogin %s
online %s
login_count %s
""" % (
            self.id,
            self.created,
            self.modified,
            self.username,
            self.group_id,
            self.role,
            self.email,
            self.fullname,
            self.firstlogin,
            self.lastlogin,
            self.online,
            self.login_count
            )

class DBPhysicalHost(Base):
    __tablename__ = 'physicalhost'
    name = Column(String(128), nullable=True)
    ipaddress = Column(String(32), primary_key = True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    ports = Column(Binary)
    freeportstart = Column(Integer)
    virtualhosts = relationship("DBVirtualNode", backref="physical_host")

    def to_dict(self):
        vhosts = []
        for vhost in self.virtualhosts:
            vhosts.append(vhost.to_dict())

        return {
            'created': str(self.created),
            'modified': str(self.modified),
            'name': self.name,
            'ipaddress': self.ipaddress,
            'freeportstart': self.freeportstart,
            'virtualhosts': vhosts
        }

    def __repr__(self):
        return """
DBPhysicalHost:
ipaddress %s
name %s
created %s
modified %s
freeportstart %s
virtualhosts %s
""" % (
            self.ipaddress,
            self.name,
            self.created,
            self.modified,
            self.freeportstart,
            self.virtualhosts
            )

class DBApplication(Base):
    __tablename__ = 'application'
    cluster_id = Column(String, primary_key=True)
    name = Column(String(128), nullable=False)

    # the cidr address for all the nodes belonging to this
    # application. eg. 10.0.1

    vipnetwork = Column(String(32), unique = True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    owner = Column(Integer, ForeignKey("user.id"))
    atype = Column(Integer)
    nodes = relationship("DBVirtualNode", backref="application")
    astate = Column(Integer)

    def to_dict(self):
        query = session.query(DBUser)
        owner = query.filter(DBUser.id == self.owner).one()
        vhosts = []
        for vhost in self.nodes:
            vhosts.append(vhost.to_dict())

        return {
            'id': self.id,
            'created': str(self.created),
            'modified': str(self.modified),
            'atype': self.atype,
            'nodes': vhosts,
            'owner': owner,
            'astate': self.astate
        }

    def __repr__(self):
        return """
DBApplication:
cluster_id %s
name %s
created %s
modified %s
vipnetwork %s
owner %s
astate %s
nodes %s
""" % (
            self.cluster_id,
            self.name,
            self.created,
            self.modified,
            self.vipnetwork,
            self.owner,
            self.astate,
            self.nodes
            )
    
class DBVirtualNode(Base):
    __tablename__ = 'virtualnode'
    id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    vipaddress = Column(String(32), nullable=False)
    port = Column(Integer)
#    pipaddress = Column(String(32))
    application_id = Column(Integer, ForeignKey('application.cluster_id'))
    docker_id = Column(String)
    vstate = Column(Integer)
    pipaddress = Column(String, ForeignKey('physicalhost.ipaddress'))

    def to_dict(self):
        query = session.query(DBApplication)
        application = query.filter(DBApplication.id == self.application_id).one()

        query = session.query(DBPhysicalHost)
        host = query.filter(DBPhysicalHost.pipaddress == self.pipaddress).one()

        return {
            'id': self.id,
            'created': str(self.created),
            'modified': str(self.modified),
            'vipaddress': self.vipaddress,
            'port': self.port,
            'application': application.to_dict(),
            'host': host.to_dict(),
            'docker_id': self.docker_id,
            'vstate': vstate
        }

    def __repr__(self):
        return """
DBVirtualNode:
id %s
created %s
modified %s
vipaddress %s
port %s
pipaddress %s
application_id %s
docker_id %s
vstate = %s
""" % (
            self.id,
            self.created,
            self.modified,
            self.vipaddress,
            self.port,
            self.pipaddress,
            self.application_id,
            self.docker_id,
            self.vstate
            )

class DBDatastore(Base):
    __tablename__ = 'datastore'
    id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    name = Column(String, unique = True)
    dtype = Column(Integer)
    source_path = Column(String) # path on the host
    container_path = Column(String, nullable = False) # path within the container
    backing_volume = Column(String) # backing volume if relevant
    application_id = Column(Integer, ForeignKey('application.cluster_id'))
    size = Column(Integer)
    tier = Column(Integer)
    state = Column(Integer)

    def to_dict(self):
        query = session.query(DBApplication)
        application = query.filter(DBApplication.id == self.application_id).one()

        return {
            'id': self.id,
            'created': str(self.created),
            'modified': str(self.modified),
            'name': self.name,
            'dtype': self.dtype,
            'source_path': self.source_path,
            'container_path': self.container_path,
            'backing_volume': self.backing_volume,
            'application': application.to_dict(),
            'size': self.size,
            'tier': self.tier,
            'state': self.state
        }

    def __repr__(self):
        return """
DBDatastore:
id %s
created %s
modified %s
name %s
dtype %s
source_path %s
container_path %s
backing_volume %s
application_id %s
""" % (
            self.id,
            self.created,
            self.modified,
            self.name,
            self.dtype,
            self.source_path,
            self.container_path,
            self.backing_volume,
            self.application_id
            )

engine = create_engine(CONFIG_DB, connect_args={'check_same_thread': False})
 
Base.metadata.create_all(engine)
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
session = DBSession()
