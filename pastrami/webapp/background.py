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
import traceback
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


def result_handler(task: asyncio.Task[None]) -> None:
    """
    Handles non awaited background tasks

    Arguments:
    ----------
    task: asyncio.Task
        The executed task
    """
    try:
        # Retrieving the result triggers the exception (in case they exist)
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:  # pylint: disable=broad-exception-caught
        LOGGER.critical(
            "Background task `%s` died due to an unhanlded exception. Exiting...", task.get_name()
        )
        LOGGER.debug(traceback.format_exc())

        # This is brutal, but i don't know how to handle it differently
        asyncio.get_event_loop().stop()


async def purge_expired(settings: Settings, idle: int = 60) -> None:
    """
    Infinite loop that purges stales Texts from the database.

    Arguments:
    ----------
    settings: Settings:
        App wide settings
    idle: int
        Wait time between loops in seconds. Default: 60
    """
    while True:
        try:
            async with Database(**settings.database.model_dump()) as database:
                LOGGER.info("Purging expired texts")
                await database.purge_expired()
        except BrokenPipeError as error:
            LOGGER.warning(str(error))

        await asyncio.sleep(idle)


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

    # Non awaited tasks are executed in the background
    async_purge_expired = asyncio.create_task(
        purge_expired(settings=settings, idle=60), name="Purge Expired"
    )
    # Asyncronously catch the exceptions
    async_purge_expired.add_done_callback(result_handler)

    # Return control to FastAPI
    yield
