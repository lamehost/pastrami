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
Implemente the API backend methods
"""

import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Response

from pastrami.database import Database, Text
from pastrami.settings import Settings

from .schema import TextSchema


def create_api(settings: Settings) -> APIRouter:
    """
    APIRouter factory.

    Generates API methods that will be included into webapp.

    Parameters:
    ----------
    settings: dict
        App configuration settings
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
        database: Database = Depends(Database(**settings.database.model_dump())),
    ) -> TextSchema:
        """
        **Add text.**

        Stores text within the database. The text is serialized as a JSON object. Both the
        `text_id` and `content` fields are mandatory. If a `text_id` is not provided, the system
        will automatically generate a UUID.
        """
        # Delete stale Texts
        await database.purge_expired(settings.dayspan)

        if len(text.content) >= settings.maxlength:
            raise HTTPException(
                status_code=406, detail=f"Text is longer than {settings.maxlength} chars."
            )

        # Add Text
        text = TextSchema.model_validate(await database.add_text(Text(**text.model_dump())))

        # Add META
        expires = text.created + datetime.timedelta(days=settings.dayspan)  # type: ignore
        response.headers["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")  # NOSONAR

        return text

    @api.head(
        "/{text_id}",
        status_code=204,
        responses={
            204: {"description": "Success"},
            404: {"description": "Not found"},
            503: {"description": "Transient error"},
        },
        tags=["API"],
    )
    async def get_metadata(
        response: Response,
        text_id: Annotated[str, Path(description="Task identifier", examples=[str(uuid4())])],
        database: Database = Depends(Database(**settings.database.model_dump())),
    ):
        """
        **Return metadata.**

        Retrieves the metadata associated with the text matching with `text_id`. Values are
        serialized as HTTP headers.
        """
        # Delete stale Texts
        await database.purge_expired(settings.dayspan)

        # Get text
        try:
            text = await database.get_text(text_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail=f"Unable to find text: {text_id}"
            ) from error

        # Populate meta
        expires = text["created"] + datetime.timedelta(days=settings.dayspan)
        response.headers["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")  # NOSONAR
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
        text_id: Annotated[str, Path(description="Task identifier", examples=[str(uuid4())])],
        database: Database = Depends(Database(**settings.database.model_dump())),
    ) -> TextSchema:
        """
        **Return Text.**

        Retrieves the Text object associated with `text_id`. Unlike the corresponding frontend
        method, this function directly returns the JSON object.
        """
        # Delete stale Texts
        await database.purge_expired(settings.dayspan)

        # Get text
        try:
            text = await database.get_text(text_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail=f"Unable to find text: {text_id}"
            ) from error

        # Add META
        expires = text["created"] + datetime.timedelta(days=settings.dayspan)
        response.headers["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")  # NOSONAR

        return TextSchema(
            text_id=str(text["text_id"]),
            content=str(text["content"]),
            created=text["created"],
        )

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
        text_id: Annotated[str, Path(description="Task identifier", examples=[str(uuid4())])],
        database: Database = Depends(Database(**settings.database.model_dump())),
    ) -> None:
        """
        **Delete Text.**

        Deletes the text matching `text_id`.
        """

        try:
            await database.delete_text(text_id)
        except ValueError as error:
            raise HTTPException(
                status_code=404, detail=f"Unable to find text: {text_id}"
            ) from error

    return api
