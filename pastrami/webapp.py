# MIT License
#
# Copyright (c) 2022, Marco Marzetti <marco@lamehost.it>
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
FastAPI app.

This module provies `create_app` which is a FastAPI app factory that provide
API and web frontend for the application.
"""

#
# Models lack the minimum amount of public methods
# Also pydantic very often raises no-name-in-module
#
# pylint: disable=too-few-public-methods, no-name-in-module


import os
from typing import Callable, Optional, Union

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, PlainTextResponse

import markdown

from pastrami.__about__ import __version__ as VERSION
from pastrami.database import Database, TextSchema
from pastrami.settings import Settings


def create_app(settings: dict = False):
    """
    FastAPI app factory.

    Parses settings from `pastrami.cfg` and returns a FastAPI instance that you
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
        settings = Settings().dict()

    # Create root webapp
    docs_url = '/docs' if settings['docs'] else False
    webapp = FastAPI(
        docs_url=docs_url,
        contact={
            "name": settings['contact']['name'],
            "url": settings['contact']['url'],
            "email": settings['contact']['email']
        },
        title="Pastrami",
        description="Pastebin web service",
        version=VERSION
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
            if response.headers['content-type'] == 'application/json':
                response.headers["Content-Security-Policy"] = \
                    "default-src 'none'"
        except KeyError:
            pass
        return response

    app_directory = os.path.dirname(os.path.realpath(__file__))

    # Static files
    static_directory = os.path.join(
        app_directory, 'static'
    )
    webapp.mount(
        "/static",
        StaticFiles(directory=static_directory, html=True),
        name="static"
    )

    # Default web page
    templates = Jinja2Templates(
        directory=os.path.join(
            app_directory, 'templates'
        )
    )

    @webapp.get(
        "/{text_id:path}",
        tags=["Frontend"]
    )
    async def index_html(
        request: Request,
        text_id: Optional[str] = False,
        database: Database = Depends(Database(**settings['database']))
    ) -> Union[PlainTextResponse, HTMLResponse, templates.TemplateResponse]:
        """
        Web frontend.

        Arguments:
        ----------
        request: Request
            The HTTP request object
        text_id: str
            Text identifier. Default: False
        database: Database
            Database instance

        Returns:
        --------
        Union[PlainTextResponse, HTMLResponse, templates.TemplateResponse]:
            Web page
        """
        # Delete stale Texts
        await database.purge_expired(settings['dayspan'])

        # Ignore common requests
        if text_id in ["favicon.ico", "index.html", "index.php"]:
            return

        # Render as text
        if text_id.lower().endswith('.txt'):
            text_id = text_id[:-4]
            text = await database.get_text(text_id)
            if not text:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unable to find text: {text_id}"
                )

            return PlainTextResponse(
                content=text['content']
            )

        # Render as markdown
        if text_id.lower().endswith('.md'):
            text_id = text_id[:-3]
            text = await database.get_text(text_id)
            if not text:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unable to find text: {text_id}"
                )

            return HTMLResponse(
                content=markdown.markdown(str(text['content']))
            )

        # Default rendering
        if text_id:
            text = await database.get_text(text_id)
            if not text:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unable to find text: {text_id}"
                )
        else:
            text = False

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                'maxlength': settings['maxlength'],
                'text': text
            }
        )

    # API
    @webapp.post(
        "/",
        response_model=TextSchema,
        responses={
            200: {"description": "Success"},
            400: {"description": "Bad request"},
            503: {"description": "Transient error"}
        },
        description="Create a nex Text",
        tags=["API"]
    )
    async def add_text(
        text: TextSchema,
        database: Database = Depends(Database(**settings['database']))
    ) -> dict:
        """
        Create Text.

        Arguments:
        ----------
        Text: TextSchema
            The schema object
        database: Database
            Database instance

        Returns:
        --------
        dict: Text Schema
        """
        # Delete stale Texts
        await database.purge_expired(settings['dayspan'])

        # Add Text
        text = await database.add_text(text)
        return TextSchema(**text)

    @webapp.delete(
        "/{text_id}",
        status_code=204,
        responses={
            204: {"description": "Success"},
            404: {"description": "Not found"},
            503: {"description": "Transient error"}
        },
        description="Deletes an existing Text from database",
        tags=["API"]
    )
    async def delete_text(
        text_id: str,
        database: Database = Depends(Database(**settings['database']))
    ) -> None:
        """
        Delete Text.

        Arguments:
        ----------
        text_id: str
            Text object ID
        database: Database
            Database instance
        """

        if not await database.delete_text(text_id):
            raise HTTPException(
                status_code=404,
                detail=f"Unable to find text: {text_id}"
            )

    return webapp
