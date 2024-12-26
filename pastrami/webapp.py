# MIT License
#
# Copyright (c) 2024, Marco Marzetti <marco@lamehost.it>
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


import datetime
import os
from typing import Callable, Optional, Union

import markdown
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pastrami.__about__ import __version__ as VERSION
from pastrami.database import Database, TextSchema
from pastrami.settings import Settings


def create_api(settings: dict) -> APIRouter:
    """
    APIRouter factory.

    Generates API methods that will be included into webapp.

    Parameters:
    ----------
    settings: dict
        App configuration settings. If False, get from configuration file.
        If file doesn't exists, get from ENV.
        Default: False

    Returns:
    --------
    APIRouter: APIRouter instance
    """

    api = APIRouter()

    @api.post(
        "/",
        response_model=TextSchema,
        responses={
            200: {"description": "Success"},
            400: {"description": "Bad request"},
            422: {"description": "Unprocessable entity"},
            503: {"description": "Transient error"},
        },
        tags=["API"],
    )
    async def add_text(
        response: Response,
        text: TextSchema,
        database: Database = Depends(Database(**settings["database"])),
    ) -> TextSchema:
        """
        **Add text.**

        Stores text within the database. The text is serialized as a JSON object. Both the
        `text_id` and `content` fields are mandatory. If a `text_id` is not provided, the system
        will automatically generate a UUID.
        """
        # Delete stale Texts
        await database.purge_expired(settings["dayspan"])

        if len(text.content) >= settings["maxlength"]:
            raise HTTPException(
                status_code=406, detail=f"Text is longer than {settings['maxlength']} chars."
            )

        # Add Text
        text = await database.add_text(text)

        # Add META
        expires = text["created"] + datetime.timedelta(days=settings["dayspan"])
        response.headers["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        return TextSchema(**text)

    @api.head(
        "/{text_id}",
        status_code=200,
        responses={
            204: {"description": "Success"},
            404: {"description": "Not found"},
            503: {"description": "Transient error"},
        },
        tags=["API"],
    )
    async def get_metadata(
        response: Response,
        text_id: Optional[str] = False,
        database: Database = Depends(Database(**settings["database"])),
    ):
        """
        **Return metadata.**

        Retrieves the metadata associated with the text matching with `text_id`. Values are
        serialized as HTTP headers.
        """
        # Delete stale Texts
        await database.purge_expired(settings["dayspan"])

        # Get text
        text = await database.get_text(text_id)
        if not text:
            raise HTTPException(status_code=404, detail=f"Unable to find text: {text_id}")

        # Populate meta
        expires = text["created"] + datetime.timedelta(days=settings["dayspan"])
        response.headers["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response.status_code = 204

    @api.get(
        "/{text_id}/raw",
        status_code=200,
        responses={
            200: {"description": "Success"},
            404: {"description": "Not found"},
            503: {"description": "Transient error"},
        },
        tags=["API"],
    )
    async def get_text(
        response: Response,
        text_id: Optional[str] = False,
        database: Database = Depends(Database(**settings["database"])),
    ) -> TextSchema:
        """
        **Return Text.**

        Retrieves the Text object associated with `text_id`. Unlike the corresponding frontend
        method, this function directly returns the JSON object.
        """
        # Delete stale Texts
        await database.purge_expired(settings["dayspan"])

        # Get text
        text = await database.get_text(text_id)
        if not text:
            raise HTTPException(status_code=404, detail=f"Unable to find text: {text_id}")

        # Add META
        expires = text["created"] + datetime.timedelta(days=settings["dayspan"])
        response.headers["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

        return TextSchema(**text)

    @api.delete(
        "/{text_id}",
        status_code=204,
        responses={
            204: {"description": "Success"},
            404: {"description": "Not found"},
            503: {"description": "Transient error"},
        },
        tags=["API"],
    )
    async def delete_text(
        text_id: str, database: Database = Depends(Database(**settings["database"]))
    ) -> None:
        """
        **Delete Text.**

        Deletes the text matching `text_id`.
        """

        if not await database.delete_text(text_id):
            raise HTTPException(status_code=404, detail=f"Unable to find text: {text_id}")

    return api


def create_frontend(settings: dict) -> APIRouter:
    """
    APIRouter factory.

    Generates frontend methods that will be included into webapp.

    Parameters:
    ----------
    settings: dict
        App configuration settings. If False, get from configuration file.
        If file doesn't exists, get from ENV.
        Default: False

    Returns:
    --------
    APIRouter: APIRouter instance
    """

    frontend = APIRouter()

    # Default web page
    app_directory = os.path.dirname(os.path.realpath(__file__))
    templates = Jinja2Templates(directory=os.path.join(app_directory, "templates"))

    @frontend.get("/{text_id}", tags=["Frontend"], response_model=None)
    async def show_text_in_web_page(
        request: Request,
        text_id: Optional[str] = False,
        database: Database = Depends(Database(**settings["database"])),
    ) -> Union[PlainTextResponse, HTMLResponse, templates.TemplateResponse]:
        """
        **Show text in web page.**

        Retrieves the Text object associated with `text_id`. By default Text content is formated
        as HTML page and colorized with Google Code Prettify stylesheet. Other formatting options
        can be returned by attaching an extension at the end of `text_id`:
         - **No extension**: Google Code Prettify (default)
         - **.txt**: Regular text file
         - **.md**: Content is interpreted as Markdown and rendered as HTML
        """
        # Delete stale Texts
        await database.purge_expired(settings["dayspan"])

        # Ignore common requests
        if text_id in ["favicon.ico", "index.html", "index.php"]:
            return

        # Find extension
        try:
            text_id, extension = text_id.lower().rsplit(".", 1)
        except ValueError:
            extension = False

        # Get text from database
        text = await database.get_text(text_id)
        if not text:
            raise HTTPException(status_code=404, detail=f"Unable to find text: {text_id}")

        # Add META
        expires = text["created"] + datetime.timedelta(days=settings["dayspan"])
        headers = {"expires": expires.strftime("%a, %d %b %Y %H:%M:%S GMT")}

        # Render as plain text
        if extension == "txt":
            return PlainTextResponse(content=text["content"], headers=headers)

        # Render as markdown
        if extension == "md":
            return HTMLResponse(content=markdown.markdown(str(text["content"])), headers=headers)

        # Render ash HTML (default)
        return templates.TemplateResponse(
            "index.html.jinja2",
            {"request": request, "maxlength": settings["maxlength"], "text": text},
            headers=headers,
        )

    @frontend.get("/", tags=["Frontend"], response_model=None)
    async def show_web_page(
        request: Request,
    ) -> HTMLResponse:
        """
        **Show default web page.**
        """

        return templates.TemplateResponse(
            "index.html.jinja2",
            {"request": request, "maxlength": settings["maxlength"], "text": False},
        )

    return frontend


def create_app(settings: dict = False):
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
        settings = Settings().dict()

    # Create root webapp
    docs_url = "/docs" if settings["docs"] else False
    webapp = FastAPI(
        docs_url=docs_url,
        contact={
            "name": settings["contact"]["name"],
            "url": settings["contact"]["url"],
            "email": settings["contact"]["email"],
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
