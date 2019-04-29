# -*- coding: utf-8 -*-

from __future__ import absolute_import

import random
import sys

from string import ascii_letters, digits
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError as DBIntegritiError


def random_id(lenght=6):
    return ''.join(
        random.choice(
            ascii_letters + digits
        ) for _ in range(lenght)
    )


BASE = declarative_base()


class PastramiDB():
    def __init__(self, path='pastrami.db'):
        if path == ":memory:":
            DB_URI = 'file::memory:?cache=shared'
            PY2 = sys.version_info.major == 2
            if PY2:
                params = {}
            else:
                params = {'uri': True}
            import sqlite3
            creator = lambda: sqlite3.connect(DB_URI, **params)
            self.engine = create_engine('sqlite:///:memory:', creator=creator, convert_unicode=True)
        else:
            self.engine = create_engine('sqlite:///%s' %  path, convert_unicode=True)

        self.session = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        )
        self.base = BASE
        self.base.query = self.session.query_property()
        self.text = Text

        # I can't understand how to catch pysqlcipher.dbapi2.DatabaseError here
        self.base.metadata.create_all(self.engine)


class Text(BASE):
    __tablename__ = 'texts'
    text_id = Column(
        String,
        primary_key=True,
        default=random_id
    )
    text = Column(
        String,
        nullable=False
    )
    modified = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return self.text
