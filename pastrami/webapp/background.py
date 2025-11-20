# MIT License
#
# Copyright (c) 2025, Marco Marzetti <marco@lamehost.it>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This module defines the background tasks executed by the webapp.
"""

import asyncio
import logging
import signal
from contextlib import asynccontextmanager

from pastrami.database import Database
from pastrami.settings import Settings

LOGGER = logging.getLogger(__name__)


def signal_handler(signum: int) -> None:
    """
    Handles signals

    Arguments:
    ----------
    signum: int
        The signal number
    """
    match signum:  # pyright: ignore[reportMatchNotExhaustive]
        case signal.SIGINT:
            raise KeyboardInterrupt


async def purge_expired(settings: Settings) -> None:
    """
    Purges stales Texts from the database

    Arguments:
    ----------
    settings: Settings:
        App wide settings
    """
    try:
        async with Database(**settings.database.model_dump()) as database:
            LOGGER.info("Purging expired texts")
            await database.purge_expired(settings.dayspan)
    except BrokenPipeError as error:
        LOGGER.warning(str(error))


@asynccontextmanager
async def background_tasks(settings: Settings):
    """
    Starts when the webapp boots. Everything before `yield` is executed immediatelly.
    Everything after `yield` is executed right before the webapp is shutting down.

    Arguments:
    ----------
    settings: Settings
        App wide settings
    """
    try:
        # This feels hacky and I hate it, but i couldn't find any better ways
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGINT, signal_handler, signal.SIGINT)
    except (RuntimeError, ValueError) as error:
        LOGGER.error(
            "Unable to register the signal handlers. The background tasks are disabled: %s", error
        )
        yield
        return

    while True:
        await purge_expired(settings)
        await asyncio.sleep(60)

    yield
