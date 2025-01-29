# fmt: off

from typing import List, Optional

from pydantic import BaseModel, Field


class RequestBaseModel(BaseModel):
    """
    Base model containing all the fields that might be used. All fields default to None to
    allow partial updates.
    """
    var: Optional[str] = Field(
        None,
        pattern="",
        description="",
        examples=[]
    )