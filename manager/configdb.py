import os
import sys

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

CONFIG_DB = 'sqlite:////tmp/config.db'
 
Base = declarative_base()
 
class Host(Base):
    __tablename__ = 'host'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    ipaddress = Column(String(250), nullable=False)
    created = Column(String(250), nullable=False)
    modified = Column(String(250), nullable=False)
 
class Application(Base):
    __tablename__ = 'application'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    ipaddress = Column(String(250), nullable=False)
    created = Column(String(250), nullable=False)
    modified = Column(String(250), nullable=False)
    owner = Column(String(250), nullable=False)
    group = Column(String(250), nullable=False)

engine = create_engine(CONFIG_DB)
 
Base.metadata.create_all(engine)
Base.metadata.bind = engine
 
DBSession = sessionmaker(bind=engine)
session = DBSession()
