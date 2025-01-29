import traceback
from typing import TypedDict


class ErrorDetails(TypedDict, total=False):
    exception_type: str
    exception_message: str
    exception_stack_trace: str


def create(exc: Exception) -> ErrorDetails:
    return ErrorDetails(
        exception_type=exc.__class__.__name__,
        exception_message=str(exc),
        exception_stack_trace="".join(traceback.format_exception(exc.__class__, exc, exc.__traceback__)),
    )
