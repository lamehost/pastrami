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
Implemente the web frontend
"""

import datetime
import json
import os
from typing import Annotated, Union
from uuid import uuid4

import markdown
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from lxml import etree
from starlette.templating import _TemplateResponse

from pastrami.database import Database
from pastrami.settings import Settings


class PrettyJSONResponse(Response):
    """
    Response class to return prettified JSON objects
    """

    media_type = "application/json"

    def render(self, content: str) -> bytes:
        """
        Renders content as prettified JSON.

        Arguments:
        ----------
        content: str
            The content to prettify

        Returns:
        --------
        bytes: The prettified JSON encoded as UTF-8
        """
        try:
            data = json.loads(content)
        except json.decoder.JSONDecodeError as error:
            raise HTTPException(
                status_code=406, detail="This content is not JSON serializable"
            ) from error

        return json.dumps(data, indent=2).encode("utf-8")


class PrettyXMLResponse(Response):
    """
    Response class to return prettified XML objects
    """

    media_type = "text/xml"

    def render(self, content: str) -> bytes:
        """
        Renders content as prettified XML.

        Arguments:
        ----------
        content: str
            The content to prettify

        Returns:
        --------
        bytes: The prettified XML encoded as UTF-8
        """
        try:
            parser = etree.XMLParser(
                remove_blank_text=True
            )  # pylint: disable=c-extension-no-member
            data = etree.XML(content, parser)  # pylint: disable=c-extension-no-member
        except etree.XMLSyntaxError as error:  # pylint: disable=c-extension-no-member
            raise HTTPException(
                status_code=406, detail="This content is not XML serializable"
            ) from error

        etree.indent(data, space="    ")
        return etree.tostring(data)


def create_frontend(settings: Settings) -> APIRouter:
    """
    APIRouter factory.

    Generates frontend methods that will be included into webapp.

    Parameters:
    ----------
    settings: Settings
        App configuration settings
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
        text_id: Annotated[str, Path(description="Task identifier", examples=[str(uuid4())])],
        database: Database = Depends(Database(**settings.database.model_dump())),
    ) -> Union[
        PlainTextResponse,
        HTMLResponse,
        _TemplateResponse,
        PrettyJSONResponse,
        PrettyXMLResponse,
        None,
    ]:
        """
        **Show text in web page.**

        Retrieves the Text object associated with `text_id`. By default Text content is formated
        as HTML page and colorized with Google Code Prettify stylesheet. Other formatting options
        can be returned by attaching an extension at the end of `text_id`:
         - **No extension**: Google Code Prettify (default)
         - **.md**: Interpreted as Markdown and rendered as HTML
         - **.json**: Prettified JSON object
         - **.txt**: Text file
         - **.xml**: Prettified XML object
        """
        # Delete stale Texts
        await database.purge_expired(settings.dayspan)

        # Ignore common requests
        if text_id in ["favicon.ico", "index.html", "index.php"]:
            raise HTTPException(status_code=404, detail=f"Unable to find text: {text_id}")

        # Find extension
        try:
            text_id, extension = text_id.lower().rsplit(".", 1)
        except ValueError:
            extension = False

        # Get text from database
        try:
            text = await database.get_text(text_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail=f"Unable to find text: {text_id}"
            ) from error

        # Add META
        expires = text["created"] + datetime.timedelta(days=settings.dayspan)
        headers = {"expires": expires.strftime("%a, %d %b %Y %H:%M:%S GMT")}  # NOSONAR

        match extension:
            case "json":
                # Render as plain JSON
                return PrettyJSONResponse(content=text["content"], headers=headers)
            case "md":
                # Render as markdown
                text["content"] = markdown.markdown(str(text["content"]), extensions=['tables'])
                return templates.TemplateResponse(
                    request,
                    "markdown.jinja2",
                    {"request": request, "text": text},
                    headers=headers,
                )
            case "txt":
                # Render as plain text
                return PlainTextResponse(content=text["content"], headers=headers)
            case "xml":
                # Render as plain XML
                return PrettyXMLResponse(content=text["content"], headers=headers)
            case _:
                # Render ash HTML (default)
                return templates.TemplateResponse(
                    request,
                    "viewer.jinja2",
                    {"request": request, "maxlength": settings.maxlength, "text": text},
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
            request,
            "editor.jinja2",
            {"request": request, "maxlength": settings.maxlength, "text": False},
        )

    return frontend
