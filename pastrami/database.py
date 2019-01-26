# -*- coding: utf-8 -*-

from __future__ import absolute_import

import random

from string import ascii_letters, digits
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


def random_id(lenght=6):
    return ''.join(
        random.choice(
            ascii_letters + digits
        ) for _ in range(lenght)
    )


BASE = declarative_base()


class PastramiDB(object):
    def __init__(self, path='pastrami.db', secret=''):
        self.engine = create_engine(
            'sqlite+pysqlcipher://:%s@/%s?cipher=aes-256-cfb&kdf_iter=64000' % (secret, path),
            convert_unicode=True
        )

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
