# -*- coding: utf-8 -*-
'''
scripts.wikiarguments_console.py
Created on 01.01.2014
@author: tobixx0
'''
from __future__ import division, absolute_import, print_function
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from wikiarguments_config import SQLALCHEMY_CONNECTION  # @UnresolvedImport @UnusedImport
except:
    from piratetools42.localconfig import SQLALCHEMY_CONNECTION  # @Reimport @UnresolvedImport

logg = logging.getLogger(__name__)
logg.info("connection: %s", SQLALCHEMY_CONNECTION)
engine = create_engine(SQLALCHEMY_CONNECTION, echo=False)
Session = sessionmaker(bind=engine)
s = session = Session()
q = session.query
__builtins__.SQLALCHEMY_CONNECTION = SQLALCHEMY_CONNECTION

from piratetools42.wikiargumentsdb import *
