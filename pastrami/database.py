# -*- coding: utf-8 -*-

# MIT License

# Copyright (c) 2025, Marco Marzetti <marco@lamehost.it>

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
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Tuple, TypedDict
from urllib.parse import urlparse
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import Column, DateTime, String
from sqlalchemy.exc import DataError, IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, validates
from sqlalchemy.pool import StaticPool

LOGGER = logging.getLogger(__name__)

BASE = declarative_base()


class TextModel(BASE):
    """
    Describes database table `texts`
    """

    __tablename__ = "texts"
    text_id = Column(String(), primary_key=True, default=lambda: str(uuid4()))
    salt = Column(String(), nullable=True)
    content = Column(String(), nullable=False)
    created = Column(
        DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )
    expires = Column(DateTime, nullable=True)

    @validates("text_id")
    def validate_text_id(self, _, text_id: str) -> str:
        """
        Validates text_id length

        Arguments:
        ----------
        _: Any
            Ignored
        text_id: str
            text identifier

        Returns:
        --------
        str: text identifier
        """
        if len(text_id.strip()) < 1:
            raise ValueError("text_id cannot be empty")
        return text_id

    @validates("content")
    def validate_content(self, _, content: str) -> str:
        """
        Validates content length

        Arguments:
        ----------
        _: Any
            Ignored
        text_id: str
            content

        Returns:
        --------
        str: content
        """
        if len(content.strip()) < 1:
            raise ValueError("content cannot be empty")
        return content

    def __repr__(self):
        return str(self.content)


class Text(TypedDict):
    """Text object"""

    text_id: str
    content: str
    created: datetime
    expires: datetime


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
    secret: Optional[str] = None
        Server side encryption key
    iterations: The amount of Fernet iterations to run. Default: 1_200_000
    """

    def __init__(  # pylint: disable=too-many-positional-arguments too-many-arguments
        self,
        url: str,
        echo: bool = False,
        create: bool = False,
        secret: Optional[str] = None,
        iterations: int = 1_200_000,
    ) -> None:
        self.secret: bytes | None = secret.encode("utf-8") if secret is not None else None
        if self.secret:
            LOGGER.info("Database is encrypted")
        self.fernet_iterations = iterations

        self.__create: bool = create

        json_serializer: Callable[[Any], str] = lambda obj: json.dumps(
            obj, ensure_ascii=False, default=str
        )
        self.__engine_kwargs: dict[str, Any] = {
            "echo": echo,
            "json_serializer": json_serializer,
        }

        parsed_url = urlparse(url)
        if parsed_url.scheme.lower() == "postgresql":
            self.url = f"postgresql+asyncpg://{parsed_url.netloc}"
        elif parsed_url.scheme.lower() == "sqlite":
            # Hijacking sqlite://:memory: to make it work with asyncio and SQLAlchemy
            # Note to self: there might be better way of doing it
            if url.lower() in ["sqlite://:memory:", "sqlite:///:memory:"]:
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
            raise ValueError(error)

        self.session = None

    async def __call__(self):
        if not self.session:
            LOGGER.info("Connecting to database")
            await self.connect()

        yield self

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args: Tuple[Any], **kwargs: dict[Any, Any]):
        await self.disconnect()

    async def connect(self) -> None:
        """
        Connects instance to database.
        """
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

            make_session = async_sessionmaker(bind=engine, autoflush=False)
        except SQLAlchemyError as error:
            LOGGER.error(error)
            raise error from error

        self.session = make_session()

    async def disconnect(self) -> None:
        """
        Disconnects instance from database.
        """
        try:
            if self.session:
                await self.session.close()
        except AttributeError:
            pass

    # Crypto methods
    @staticmethod
    async def __calculate_hash(text: str) -> str:
        """
        Returns the SHA256 has of a text.

        Arguments:
        ----------
        text: str
            Plain text

        Returns:
        --------
        str: Hexadecimal string representing the SHA256 hash
        """

        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def __encrypt(self, text_id: str, salt: str, content: str) -> Tuple[str, str]:
        """
        Encrypts content using text_id as encryption key

        Arguments:
        ----------
        text_id: str
            Text ID used as encryption key
        salt: str
            Salt used during encryption
        content: str
            Content to be encrypted

        Returns:
        --------
        Tuple:
         - str: hashed text_id
         - str: encrypted content
        """
        if self.secret is None:
            raise ValueError("Secret can't be None")
        
        # Encrypt content
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode("utf-8"),
            iterations=self.fernet_iterations,
        )

        private_key = base64.urlsafe_b64encode(kdf.derive(self.secret + text_id.encode("utf-8")))

        fernet = Fernet(private_key)
        token = fernet.encrypt(content.encode("utf-8"))
        encrypted_content = base64.b64encode(token).decode("utf-8")

        text_id_hash = await self.__calculate_hash(text_id)

        return (text_id_hash, encrypted_content)

    async def __decrypt(self, text_id: str, salt: str, encrypted_content: str) -> str:
        """
        Decrypts content using text_id as decryption key

        Arguments:
        ----------
        text_id: str
            Hashed text ID
        salt: str
            Salt used during encryption
        encrypted_content: str
            Content to be decrypted

        Returns:
        --------
        str: decrypted content
        """
        if self.secret is None:
            raise ValueError("Secret can't be None")
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode("utf-8"),
            iterations=self.fernet_iterations,
        )
        private_key = base64.urlsafe_b64encode(kdf.derive(self.secret + text_id.encode("utf-8")))

        fernet = Fernet(private_key)
        token = base64.b64decode(encrypted_content.encode("utf-8"))
        content = fernet.decrypt(token).decode("utf-8")

        return content

    # Text methods
    async def add_text(self, text: Text) -> Text:
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
        if not self.session:
            raise BrokenPipeError("Not connected to the database")  # NOSONAR

        if len(text["text_id"].strip()) < 1:
            raise ValueError("text_id cannot be empty")

        if len(text["content"].strip()) < 1:
            raise ValueError("content cannot be empty")

        # Hide text_id with hashing
        original_text_id = text["text_id"]
        if self.secret is not None:
            salt = str(uuid4())
            text["text_id"], text["content"] = await self.__encrypt(
                text["text_id"], salt, text["content"]
            )
        else:
            salt = None

        db_object = TextModel(**text, salt=salt)

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

    async def get_text(self, text_id: str) -> Text:
        """
        Gets a text from database

        Arguments:
        ----------
        text_id: ID of the text

        Returns:
        --------
        None if no text was found, otherwise the `text` formatted as dict
        """
        if not self.session:
            raise BrokenPipeError("Not connected to the database")  # NOSONAR

        # text_id is hidden with hashing
        original_text_id = text_id
        if self.secret is not None:
            text_id = await self.__calculate_hash(text_id)

        async with self.session as session:
            text = await session.run_sync(
                lambda sync_session: sync_session.query(TextModel)
                .filter(TextModel.text_id == text_id)
                .first()
            )

        if text is None:
            raise ValueError(f"Unable to find matching text. Text ID: {original_text_id}")

        if self.secret:
            try:
                content = await self.__decrypt(original_text_id, str(text.salt), str(text.content))
            except InvalidToken as error:
                raise ValueError(
                    f"Unable to decrypt content. Text ID: {original_text_id}"
                ) from error
        else:
            content = text.content

        LOGGER.debug("Text returned from the database. Text ID: %s", original_text_id)

        return Text(
            text_id=original_text_id,
            content=str(content),
            created=text.created,  # pyright: ignore[reportArgumentType]
            expires=text.expires,  # pyright: ignore[reportArgumentType]
        )

    async def delete_text(self, text_id: str):
        """
        Deletes text from database

        Arguments:
        ----------
        text_id: str
            Text identifier
        """
        if not self.session:
            raise BrokenPipeError("Not connected to the database")  # NOSONAR

        # text_id is hidden with hashing
        original_text_id = text_id
        if self.secret:
            text_id = await self.__calculate_hash(text_id)

        async with self.session as session:
            text = await session.run_sync(
                lambda sync_session: sync_session.query(TextModel)
                .filter(TextModel.text_id == text_id)
                .first()
            )

        if not text:
            raise ValueError(f"Unable to find matching text. Text ID: {original_text_id}")

        async with self.session as session:
            async with session.begin():
                try:
                    await session.delete(text)
                    await session.commit()
                except (DataError, OperationalError) as error:
                    await session.rollback()
                    raise RuntimeError(error) from error

        LOGGER.debug("Text deleted from the database. Text ID: %s", original_text_id)

    async def purge_expired(self) -> int:
        """
        Deletes expired Texts from database

        Returns:
        --------
        int: amount of Texts that have been deleted
        """
        if not self.session:
            raise BrokenPipeError("Not connected to the database")  # NOSONAR

        async with self.session as session:
            texts = await session.run_sync(
                lambda sync_session: sync_session.query(TextModel)
                .filter(TextModel.expires < datetime.now(timezone.utc))
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

        LOGGER.debug("Expired text deleted from the database: %d", len(texts))

        return len(texts)
