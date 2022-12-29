# -*- coding: utf-8 -*-

# MIT License

# Copyright (c) 2022, Marco Marzetti <marco@lamehost.it>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

#
# Models lack the minimum amount of public methods
# Also pydantic very often raises no-name-in-module
#
# pylint: disable=too-few-public-methods, no-name-in-module

import logging
from urllib.parse import urlparse
from typing import Union
import json
import random
from string import ascii_letters, digits
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    DataError,
    OperationalError
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)

BASE = declarative_base()


def random_id(lenght=8):
    return ''.join(
        random.SystemRandom().choice(
            ascii_letters + digits
        ) for _ in range(lenght)
    )


class TextModel(BASE):
    __tablename__ = 'texts'
    text_id = Column(
        String,
        primary_key=True,
        default=random_id
    )
    content = Column(
        String,
        nullable=False
    )
    modified = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return str(self.content)


class TextSchema(BaseModel):
    """
    Defines the model to describe a Text
    """
    text_id: str = Field(
        description="Task identifier",
        default_factory=random_id
    )

    content: str = Field(
        description="Text content"
    )

    modified: datetime = Field(
        description="Last moment the text was modified",
        default_factory=datetime.utcnow
    )


class DuplicatedItemException(Exception):
    """
    Raised when a duplicated item is created
    """
    def __init__(self, object_type: str, object_id: str) -> None:
        self.object_id = object_id
        self.object_type = object_type
        super().__init__(
            f"Duplicated object id '{object_id}' for object type '{object_type}'"  # noqa
        )


class Database():
    """
    SQL database abstraction class. Allows users to create, read and delete
    Texts

    Arguments:
    ----------
    url: database url
    echo: whether echo SQL queries or not
    create_tables: whether create SQL tables or not
    session: Session object used to connect to the DB. By default a new one
             is created
    """

    def __init__(
        self,
        url: str,
        echo: bool = False,
        create_tables: bool = False,
        session: Union[bool, AsyncSession] = False,
    ) -> None:
        parsed_url = urlparse(url)
        self.__create_tables = create_tables
        self.__engine_kwargs = {
            "echo": echo,
            "json_serializer": lambda obj: json.dumps(
                obj,
                ensure_ascii=False,
                default=str
            )
        }
        # We only need SQLite for unittest, but we're going to make it a
        # first class citizen anyway
        if parsed_url.scheme.lower() == 'postgresql':
            self.url = f'postgresql+asyncpg://{parsed_url.netloc}'
        elif parsed_url.scheme.lower() == 'sqlite':
            if url.lower() == 'sqlite:///:memory:':
                self.url = 'sqlite+aiosqlite:///:memory:'
            else:
                self.url = f'sqlite+aiosqlite://{parsed_url.netloc}{parsed_url.path}'  # noqa
            # StaticPool is needed when SQLite is ran in memory
            self.__engine_kwargs['poolclass'] = StaticPool
            self.__engine_kwargs['connect_args'] = {"check_same_thread": False}
        else:
            error = (
                f'Database can be either "sqlite" or "postgresql", not: "{parsed_url.scheme}"'   # pylint: disable=line-too-long   # noqa
            )
            # LOGGER.error(error)
            raise ValueError(error)

        if session and isinstance(session, bool):
            raise ValueError('Session can be either false or AsyncSession')
        self.session = session

    async def __call__(self):
        if not self.session:
            LOGGER.info('Connecting to database')
            await self.connect()

        yield self

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args, **kwargs):
        try:
            await self.session.close()
        except AttributeError:
            pass

    async def connect(self, force: bool = False) -> None:
        """
        Connects instance to database.

        Arguments:
        ----------
        force: bool
            Force reconnection even if a session exists already. Default: False
        """
        if self.session:
            if not force:
                return self.session

        try:
            engine = create_async_engine(self.url, **self.__engine_kwargs)

            # Create tables if requested
            if self.__create_tables:
                try:
                    async with engine.begin() as connection:
                        await connection.run_sync(BASE.metadata.create_all)
                    LOGGER.info('Connected to database')
                except OperationalError as error:
                    LOGGER.error(error)
                    raise RuntimeError(error) from error

            make_session = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
                class_=AsyncSession
            )

        except SQLAlchemyError as error:
            LOGGER.error(error)
            raise error from error

        self.session = make_session()

    async def add_text(
        self,
        text: Union[TextSchema, dict]
    ) -> dict:
        """
        Adds text to database

        Arguments:
        ----------
        text: TextSchema or dict
            Text object

        Returns:
        --------
        dict: Text object
        """
        text = TextSchema.parse_obj(text).dict()

        db_object = TextModel(
            text_id=str(text['text_id']),
            content=text['content'],
            modified=text['modified']
        )

        async with self.session as session:
            async with session.begin():
                session.add(db_object)

                try:
                    await session.commit()
                    # await session.refresh(db_object)
                except (DataError, OperationalError) as error:
                    await session.rollback()
                    raise RuntimeError(error) from error
                except IntegrityError as error:
                    await session.rollback()
                    if "unique" in str(error.orig).lower().split(' '):
                        raise DuplicatedItemException(
                            object_type='text', object_id=text['text_id']
                        ) from error

        LOGGER.debug(
            'New text added to database %s: Text ID: %s',
            text['text_id'],
            text
        )

        return await self.get_text(str(text['text_id']))

    async def get_text(self, text_id: str) -> Union[dict, None]:
        """
        Gets a text from database

        Arguments:
        ----------
        text_id: ID of the text

        Returns:
        --------
        None if no text was found, otherwise the `text` formatted as dict
        """
        async with self.session as session:
            text = await session.run_sync(
                lambda sync_session: sync_session.query(
                    TextModel
                ).filter(
                    TextModel.text_id == str(text_id)
                ).first()
            )

        if text is None:
            return None

        return TextSchema.parse_obj(
            {
                "text_id": str(text_id),
                "content": text.content,
                "modified": text.modified
            }
        ).dict()

    async def delete_text(self, text_id: str) -> bool:
        """
        Deletes text from database

        Arguments:
        ----------
        text_id: str
            Text identifier

        Returns:
        --------
        True if the text was deleted, otherwise False
        """
        async with self.session as session:
            text = await session.run_sync(
                lambda sync_session: sync_session.query(
                    TextModel
                ).filter(
                    TextModel.text_id == text_id
                ).first()
            )

        if not text:
            return False

        async with self.session as session:
            async with session.begin():
                try:
                    await session.delete(text)
                    await session.commit()
                except (DataError, OperationalError) as error:
                    await session.rollback()
                    raise RuntimeError(error) from error

        LOGGER.debug(
            'Text deleted from the database. Text ID: %s',
            text_id
        )

        return True

    async def purge_expired(self, days: int) -> int:
        """
        Deletes expired Texts from database

        Arguments:
        ----------
        days: int
            Delete Texts older than `days`

        Returns:
        --------
        int: amount of Texts that have been deleted
        """

        expire_date = datetime.now() - timedelta(days)

        async with self.session as session:
            texts = await session.run_sync(
                lambda sync_session: sync_session.query(
                    TextModel
                ).filter(
                    TextModel.modified < expire_date
                ).all()
            )

        if not texts:
            return 0

        async with self.session as session:
            async with session.begin():
                try:
                    for text in texts:
                        await session.delete(text)
                    await session.commit()
                except (DataError, OperationalError) as error:
                    await session.rollback()
                    raise RuntimeError(error) from error

        LOGGER.debug(
            'Expired text deleted from the database (%d)',
            len(texts)
        )

        return len(texts)
