import asyncio
from typing import Any, Callable, Awaitable
from typing import Optional, Sequence, Union

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from middleware.error_middleware import UnhandledExceptionsMiddleware
from model.problem.response import ProblemResponse

PreHook = Callable[[Request, Exception], Union[Any, Awaitable[Any]]]
PostHook = Callable[[Request, Response, Exception], Union[Any, Awaitable[Any]]]


def init(
    app: FastAPI,
    pre_hooks: Optional[Sequence[PreHook]] = None,
    post_hooks: Optional[Sequence[PostHook]] = None,
) -> None:
    """
    Register the FastAPI RFC7807 middleware with a FastAPI application instance.

    This function registers three things:

    1. An exception handler for HTTPExceptions. This ensures that any HTTPException
       raised by the application is properly converted to an RFC7807 Problem response.
    2. An exception handler for RequestValidationError. This ensures that any validation
       errors (e.g. incorrect params) are formatted into an RFC7807 Problem response.
    3. UnhandledExceptionsMiddleware. This middleware handles all other exceptions raised
       by the application and converts them to RFC7807 Problem responses.

    It is important to note that the ProblemMiddleware which gets registered with
    the application overrides starlette's internal default ServerErrorMiddleware
    by capturing all exceptions before they make it to that handler. As such, this
    means that all errors should return as JSON, but also that previous behavior, e.g.
    of having debug tracebacks for errors displayed in HTML will no longer occur.

    Args:
        app: The FastAPI application instance to register with.
        pre_hooks: Functions which are run before generating a response.
        post_hooks: Functions which are run after generating a response.
    """
    _handler = problem_exception_handler_provider(pre_hooks=pre_hooks, post_hooks=post_hooks)

    app.add_exception_handler(HTTPException, handler=_handler)
    app.add_exception_handler(RequestValidationError, handler=_handler)
    # noinspection PyTypeChecker
    app.add_middleware(UnhandledExceptionsMiddleware, handler=_handler)


def problem_exception_handler_provider(
    pre_hooks: Optional[Sequence[PreHook]] = None,
    post_hooks: Optional[Sequence[PostHook]] = None,
) -> Callable:
    """
    A custom FastAPI exception handler constructor.

    The provider is used to return an RFC7807 compliant ProblemResponse
    for the given exception.

    Hooks can be specified for the handler as well. These hooks run before the
    exception is converted into a ProblemResponse and returned. Hooks must take
    a request (starlette.requests.Request) and an Exception as its arguments.

    If the hook raises an exception, the exception is ignored. Hooks can be used
    to add additional logging around exception handling, to collect application
    metrics for error counts, or for any other reason deemed suitable.

    Args:
        pre_hooks: Functions which are run before generating a response.
        post_hooks: Functions which are run after generating a response.
    """

    async def exception_handler(request: Request, exc: Exception) -> ProblemResponse:
        async def exec_hooks(hooks: Optional[Sequence[Union[PreHook, PostHook]]], *args) -> None:
            """
            Helper function to execute hooks, if any are defined.

            Args:
                hooks: The hooks, if any, to execute.
                args: Positional arguments to pass to the hooks.
            """
            if hooks:
                for hook in hooks:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(*args)
                    else:
                        hook(*args)

        nonlocal pre_hooks, post_hooks
        await exec_hooks(pre_hooks, request, exc)
        response = ProblemResponse(request, exc)
        await exec_hooks(post_hooks, request, response, exc)

        return response

    return exception_handler
