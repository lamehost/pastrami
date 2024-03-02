# -*- coding: utf-8 -*-

# MIT License

# Copyright (c) 2024, Marco Marzetti <marco@lamehost.it>

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

"""
Database abstraction module for the package
"""

import base64
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Tuple, Union
from urllib.parse import urlparse
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, String
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

LOGGER = logging.getLogger(__name__)

BASE = declarative_base()


class TextModel(BASE):
    """
    Describes database table `texts`
    """

    __tablename__ = "texts"
    text_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    content = Column(String, nullable=False)
    created = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return str(self.content)


class SaltModel(BASE):
    """
    Describes database table `salt`
    """

    __tablename__ = "salt"
    salt = Column(String, primary_key=True)

    def __repr__(self):
        return str(self.content)


class TextSchema(BaseModel):
    """
    Defines the model to describe a Text
    """

    text_id: str = Field(description="Task identifier", default_factory=lambda: str(uuid4()))

    content: str = Field(description="Text content")

    created: datetime = Field(
        description="Last moment the text was created", default_factory=datetime.utcnow
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


class Database:
    """
    SQL database abstraction class. Allows users to create, read and delete
    Texts

    Arguments:
    ----------
    url: str
        Database url
    echo: bool
        Whether echo SQL queries or not. Default: False
    create: bool
        Whether create SQL database and tables or not. Default: False
    encrypted: bool
        Whether encrypt data or not. Default: False
    session: Session object used to connect to the DB. By default a new one
             is created
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        url: str,
        echo: bool = False,
        create: bool = False,
        encrypted: bool = False,
        session: Union[bool, AsyncSession] = False,
    ) -> None:
        self.__encrypted = encrypted

        parsed_url = urlparse(url)
        self.__create = create
        self.__engine_kwargs = {
            "echo": echo,
            "json_serializer": lambda obj: json.dumps(obj, ensure_ascii=False, default=str),
        }
        # We only need SQLite for unittest, but we're going to make it a
        # first class citizen anyway
        if parsed_url.scheme.lower() == "postgresql":
            self.url = f"postgresql+asyncpg://{parsed_url.netloc}"
        elif parsed_url.scheme.lower() == "sqlite":
            if url.lower() == "sqlite://:memory:":
                self.url = "sqlite+aiosqlite://"
                # Enforce shared cache
                self.__engine_kwargs["creator"] = lambda: sqlite3.connect(
                    "file::memory:?cache=shared", uri=True
                )
            else:
                self.url = f"sqlite+aiosqlite://{parsed_url.netloc}{parsed_url.path}"  # noqa
            # StaticPool is needed when SQLite is ran in memory
            self.__engine_kwargs["poolclass"] = StaticPool
            self.__engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            error = f'Database can be either "sqlite" or "postgresql", not: "{parsed_url.scheme}"'
            # LOGGER.error(error)
            raise ValueError(error)

        if session and isinstance(session, bool):
            raise ValueError("Session can be either false or AsyncSession")
        self.session = session

    async def __call__(self):
        if not self.session:
            LOGGER.info("Connecting to database")
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
            if self.__create:
                try:
                    async with engine.begin() as connection:
                        await connection.run_sync(BASE.metadata.create_all)
                    LOGGER.info("Connected to database")
                except OperationalError as error:
                    LOGGER.error(error)
                    raise RuntimeError(error) from error

            make_session = sessionmaker(
                autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
            )
        except SQLAlchemyError as error:
            LOGGER.error(error)
            raise error from error

        self.session = make_session()

    # Crypto methods
    @staticmethod
    async def __encrypt_text_id(text_id: [str, bytes]) -> str:
        """
        Returns and encrypted version a Text identier.

        Arguments:
        ----------
        text_id: str or bytes
            Unencrypted text identier

        Returns:
        --------
        str: encrypted Text identifier
        """
        if not isinstance(text_id, bytes):
            text_id = text_id.encode("utf-8")
        return str(hashlib.sha256(text_id).hexdigest())

    async def __encrypt(self, text_id: [str, bytes], content: str) -> Tuple[str, bytes]:
        """
        Encrypts content using text_id as encryption key

        Arguments:
        ----------
        text_id: str or bytes
            Text ID used as encryption key
        content: str
            Content to be encrypted

        Returns:
        --------
        Tuple:
         - encrypted Text identifier
         - encrypted content
        """
        if not isinstance(text_id, bytes):
            text_id = text_id.encode("utf-8")

        encrypted_text_id = await self.__encrypt_text_id(text_id)

        salt = await self.get_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode("utf-8"),
            iterations=480000,
        )
        private_key = base64.urlsafe_b64encode(kdf.derive(text_id))

        fernet = Fernet(private_key)
        token = fernet.encrypt(content.encode("utf-8"))
        encrypted_content = base64.b64encode(token)

        return (encrypted_text_id, encrypted_content)

    async def __decrypt(self, text_id: [str, bytes], encrypted_content: bytes) -> str:
        """
        Decrypts content using text_id as decryption key

        Arguments:
        ----------
        text_id: str or bytes
            Text ID used as decryption key
        encrypted_content: str
            Content to be decrypted

        Returns:
        --------
        str: decrypted content
        """
        if not isinstance(text_id, bytes):
            text_id = text_id.encode("utf-8")

        salt = await self.get_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode("utf-8"),
            iterations=480000,
        )
        private_key = base64.urlsafe_b64encode(kdf.derive(text_id))

        token = base64.b64decode(encrypted_content)

        fernet = Fernet(private_key)
        return fernet.decrypt(token).decode("utf-8")

    # Salt methods
    async def get_salt(self) -> str:
        """
        Gets salt from database. If salt is missing, it creates it

        Returns:
        --------
        str: salt
        """
        # Get salt from database
        async with self.session as session:
            db_object = await session.run_sync(
                lambda sync_session: sync_session.query(SaltModel).first()
            )

        if db_object is not None:
            return db_object.salt

        # Generate salt if missing
        async with self.session as session:
            salt = str(uuid4())
            async with session.begin():
                session.add(SaltModel(salt=salt))

                try:
                    await session.commit()
                except (DataError, OperationalError) as error:
                    await session.rollback()
                    raise RuntimeError(error) from error

        return salt

    # Text methods
    async def add_text(self, text: Union[TextSchema, dict]) -> dict:
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

        # Hide text_id with hashing
        original_text_id = text["text_id"]
        if self.__encrypted:
            text["text_id"], text["content"] = await self.__encrypt(
                text["text_id"], text["content"]
            )

        db_object = TextModel(**text)

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
                    if "unique" in str(error.orig).lower().split(" "):
                        raise DuplicatedItemException(
                            object_type="text", object_id=original_text_id
                        ) from error

        LOGGER.debug("New text added to database %s: Text ID: %s", text, original_text_id)

        return await self.get_text(original_text_id)

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

        # text_id is hidden with hashing
        original_text_id = text_id
        if self.__encrypted:
            text_id = await self.__encrypt_text_id(text_id)

        async with self.session as session:
            text = await session.run_sync(
                lambda sync_session: sync_session.query(TextModel)
                .filter(TextModel.text_id == str(text_id))
                .first()
            )

        if text is None:
            return None

        if self.__encrypted:
            try:
                content = await self.__decrypt(original_text_id, text.content)
            except InvalidToken:
                LOGGER.debug("Unable to decrypt content. Text ID: %s", original_text_id)
                return None
        else:
            content = text.content

        return TextSchema(text_id=original_text_id, content=content, created=text.created).dict()

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
        # text_id is hidden with hashing
        original_text_id = text_id
        if self.__encrypted:
            text_id = await self.__encrypt_text_id(text_id)

        async with self.session as session:
            text = await session.run_sync(
                lambda sync_session: sync_session.query(TextModel)
                .filter(TextModel.text_id == text_id)
                .first()
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

        LOGGER.debug("Text deleted from the database. Text ID: %s", original_text_id)

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
                lambda sync_session: sync_session.query(TextModel)
                .filter(TextModel.created < expire_date)
                .all()
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

        LOGGER.debug("Expired text deleted from the database (%d)", len(texts))

        return len(texts)
