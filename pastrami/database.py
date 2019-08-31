# -*- coding: utf-8 -*-

# MIT License

# Copyright (c) 2019, Marco Marzetti <marco@lamehost.it>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

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
