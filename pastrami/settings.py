"""
This module provides data models and methods to read the settings file
"""

#
# Models lack the minimum amount of public methods
# Also pydantic very often raises no-name-in-module
#
# pylint: disable=too-few-public-methods, no-name-in-module

from enum import Enum

from pydantic import AnyHttpUrl, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """
    Database specific settings
    """

    url: str = "sqlite:///pastrami.db"
    create: bool = True
    echo: bool = False
    encrypted: bool = False


class ContactSettings(BaseSettings):
    """
    Contact specific settings
    """

    name: str
    url: AnyHttpUrl
    email: EmailStr


class LogLevelEnums(str, Enum):
    """
    Supported logging levels
    """

    FATAL = "FATAL"
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class Settings(BaseSettings):
    """
    Settings passed to the AWSGI application
    """

    database: DatabaseSettings
    contact: ContactSettings

    # Text specs
    dayspan: int = 90
    maxlength: int = 10000

    # Activate API docs
    docs: bool = False

    # Loglevel
    loglevel: LogLevelEnums = LogLevelEnums.WARNING

    model_config = SettingsConfigDict(
        extra="forbid", env_file="pastrami.conf", env_prefix="pastrami_", env_nested_delimiter="_"
    )
