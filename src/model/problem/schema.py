from typing import Optional, List

from pydantic import BaseModel


class Problem(BaseModel):
    """Model of the RFC7807 Problem response schema."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
    errors: Optional[List[dict]] = None
