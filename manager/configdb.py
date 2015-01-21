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
 
class PhysicalHost(Base):
    __tablename__ = 'physicalhost'
    name = Column(String(250), nullable=True)
    ipaddress = Column(String(32), primary_key = True)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    ports = Column(Binary)

class Application(Base):
    __tablename__ = 'application'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    ipaddress = Column(String(32), nullable=False)
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)
    owner = Column(String(250), nullable=False)
    group = Column(String(250), nullable=False)
    nodes = relationship("VirtualNode", backref="application")

class VirtualNode(Base):
    __tablename__ = 'virtualnode'
    id = Column(String(64), primary_key=True) # 'ipaddress:port'
    ipaddress = Column(String(32), nullable=False)
    port = Column(Integer, nullable=False)
    subnet = Column(String(16), nullable=False)
    application_id = Column(Integer, ForeignKey('application.id'))
    created = Column(DateTime, nullable=False)
    modified = Column(DateTime, nullable=False)

engine = create_engine(CONFIG_DB)
 
Base.metadata.create_all(engine)
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
session = DBSession()
