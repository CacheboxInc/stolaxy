#!/usr/bin/env python3

import os
import sys

from sqlalchemy import Binary, Column, ForeignKey, Integer, String, DateTime
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
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    name = Column(String, unique = True)
    group_id = Column(Integer, ForeignKey('group.id'))

    def __repr__(self):
        return """
DBUser:
id %s
created %s
modified %s
name %s
group_id %s
""" % (
            self.id,
            self.created,
            self.modified,
            self.name,
            self.group_id
            )

class DBPhysicalHost(Base):
    __tablename__ = 'physicalhost'
    name = Column(String(128), nullable=True)
    ipaddress = Column(String(32), primary_key = True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    ports = Column(Binary)
    freeportstart = Column(Integer)

    def __repr__(self):
        return """
DBPhysicalHost:
ipaddress %s
name %s
created %s
modified %s
freeportstart %s
""" % (
            self.ipaddress,
            self.name,
            self.created,
            self.modified,
            self.freeportstart
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
    nodes = relationship("DBVirtualNode", backref="application")

    def __repr__(self):
        return """
DBApplication:
cluster_id %s
name %s
created %s
modified %s
vipnetwork %s
owner %s
nodes %s
""" % (
            self.cluster_id,
            self.name,
            self.created,
            self.modified,
            self.vipnetwork,
            self.owner,
            self.nodes
            )
    
class DBVirtualNode(Base):
    __tablename__ = 'virtualnode'
    id = Column(Integer, primary_key=True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    vipaddress = Column(String(32), nullable=False)
    port = Column(Integer)
    pipaddress = Column(String(32))
    application_id = Column(Integer, ForeignKey('application.cluster_id'))
    docker_id = Column(String)

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
""" % (
            self.id,
            self.created,
            self.modified,
            self.vipaddress,
            self.port,
            self.pipaddress,
            self.application_id,
            self.docker_id
            )

engine = create_engine(CONFIG_DB)
 
Base.metadata.create_all(engine)
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
session = DBSession()
