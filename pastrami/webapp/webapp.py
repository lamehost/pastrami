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
This module provides `create_app` which is a FastAPI app factory that provide
API and web frontend for the application.
"""

import os
from typing import Callable, Optional

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from pastrami.__about__ import __version__ as VERSION
from pastrami.settings import Settings

from .api import create_api
from .frontend import create_frontend


def create_app(settings: Optional[Settings] = None):
    """
    FastAPI app factory.

    Parses settings from `pastrami.conf` and returns a FastAPI instance that you
    can run via uvicorn.

    Parameters:
    ----------
    api_mount_point: str
        Path the API will be mounted on. (Default: '/api/')
    settings: dict
        App configuration settings. If False, get from configuration file.
        If file doesn't exists, get from ENV.
        Default: False

    Returns:
    --------
    Fastapi: FastAPI app instance
    """
    # Read settings
    if not settings:
        settings = Settings()  # type: ignore

    # Create root webapp
    docs_url = "/docs" if settings.docs else None
    webapp = FastAPI(
        docs_url=docs_url,
        contact={
            "name": settings.contact.name,
            "url": settings.contact.url,
            "email": settings.contact.email,
        },
        title="Pastrami",
        description="Secure, minimalist text storage for your sensitive data",
        version=VERSION,
    )

    # Add custom headers as recommended by
    # https://github.com/shieldfy/API-Security-Checklist#output
    @webapp.middleware("http")
    async def add_custom_headers(request: Request, call_next: Callable):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "deny"
        # Force restrictive content-security-policy for JSON content
        try:
            if response.headers["content-type"] == "application/json":
                response.headers["Content-Security-Policy"] = "default-src 'none'"
        except KeyError:
            pass
        return response

    app_directory = os.path.dirname(os.path.realpath(__file__))

    # Static files
    static_directory = os.path.join(app_directory, "static")
    webapp.mount("/static", StaticFiles(directory=static_directory, html=True), name="static")

    # Frontend methods
    frontend = create_frontend(settings)
    webapp.include_router(frontend)

    # API methods
    api = create_api(settings)
    webapp.include_router(api)

    # Return webapp
    return webapp
