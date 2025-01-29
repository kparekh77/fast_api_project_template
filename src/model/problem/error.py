from typing import Any

from pydantic import BaseModel


class Error(BaseModel):
    """Represents a single error in the Problem errors list."""

    code: Any
    error: dict
