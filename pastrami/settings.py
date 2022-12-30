"""
This module provides data models and methods to read the settings file
"""

#
# Models lack the minimum amount of public methods
# Also pydantic very often raises no-name-in-module
#
# pylint: disable=too-few-public-methods, no-name-in-module

from pydantic import (
    HttpUrl,
    BaseSettings,
    EmailStr,
    Extra
)


class DatabaseSettings(BaseSettings, extra=Extra.forbid):
    """
    Database specific settings
    """
    url: str = 'sqlite:///pastrami.db'
    create: bool = True
    echo: bool = False
    encrypted: bool = False


class ContactSettings(BaseSettings, extra=Extra.forbid):
    """
    Contact specific settings
    """
    name: str
    url: HttpUrl
    email: EmailStr


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

    class Config:
        """
        Pydantic's BaseSettings configuration statements
        """
        env_file = 'pastrami.conf'
        env_prefix = 'pastrami_'
        extra = Extra.ignore
        env_nested_delimiter = '_'
