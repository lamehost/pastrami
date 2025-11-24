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
Object schemas used within the API
"""

from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, StringConstraints


class TextSchema(BaseModel):
    """
    Defines the model to describe a Text
    """

    text_id: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=36)
    ] = Field(
        description="Task identifier", default_factory=lambda: str(uuid4()), examples=[str(uuid4())]
    )
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = Field(
        description="Text content",
    )
    created: Optional[datetime] = Field(
        description="Moment the text was created",
        default_factory=lambda: datetime.now(timezone.utc),
    )
    expires: Optional[datetime] = Field(
        description="Moment the text will expire",
        default=None,
    )
