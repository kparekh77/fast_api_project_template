from __future__ import annotations

import traceback
from typing import Any, Mapping, Dict, Optional, List

from fastapi.exceptions import RequestValidationError
from repository.domain.exceptions import validation_failure_error, not_found_error, conflict_value_error
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND, HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from config.logging_configurator import ErrorLogRecord
from helpers import documentation
from model.problem.exception import ProblemException


class ProblemResponse(Response):
    """A Response for RFC7807 Problems."""

    media_type: str = "application/problem+json"

    def __init__(self, request: Request, exc: Exception) -> None:
        self.problem: ProblemException | None = None
        self.request: Request = request
        super(ProblemResponse, self).__init__(exc)

    def init_headers(self, headers: Mapping[str, str] = None) -> None:
        h = dict(headers) if headers else {}
        if hasattr(self, "problem") and self.problem.headers:
            h.update(self.problem.headers)

        super(ProblemResponse, self).init_headers(h)

    def render(self, content: Any) -> bytes:
        """Render the provided content as an RFC-7807 Problem JSON-serialized bytes."""
        if isinstance(content, ProblemException):
            p = content
        elif isinstance(content, dict):
            p = self.as_dict(content, self.request)
        elif isinstance(content, HTTPException):
            p = self.as_http_exception(content, self.request)
        elif isinstance(content, RequestValidationError):
            p = self.as_request_validation_error(content, self.request)
        elif isinstance(content, Exception):
            p = self.as_uncaught_exception(content, self.request)
        else:
            p = ProblemException(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Got unexpected content when trying to generate error response",
                instance=self.request.url.path,
                errors=[{"content": str(content)}],
            )

        # Dynamically set the response status_code to match
        # the status code of the Problem.
        self.status_code = p.status
        self.problem = p

        return p.to_bytes()

    @staticmethod
    def as_dict(data: Dict[str, Any], request: Request) -> ProblemException:
        """
        Create a new Problem instance from a dictionary.

        This uses the dictionary as keyword arguments for the Problem constructor.
        If the given dictionary does not contain any fields matching those defined
        in the RFC7807 spec, it will use defaults where appropriate (e.g. status
        code 500) and use the dictionary members as supplemental context in the
        Problem response.

        Args:
            data: The dictionary to convert into a Problem exception.
            request: The Request object that triggered the exception.

        Returns:
            A new Problem instance populated from the dictionary fields.
        """
        problem_exception = ProblemException(**data)

        # Ensure that the instance field is set to the request path
        if not problem_exception.instance:
            problem_exception.instance = request.url.path

        return problem_exception

    @staticmethod
    def as_http_exception(
        exc: HTTPException,
        request: Request,
        errors: Optional[List[Dict[str, Any]]] = None,
    ) -> ProblemException:
        """
        Create a new Problem instance from an HTTPException.

        The Problem will take on the status code of the HTTPException and generate
        a title based on that status code. If the HTTPException specifies any details,
        those will be used as the problem details.

        Args:
            exc: The HTTPException to convert into a Problem exception.
            request: The Request object that triggered the exception.
            errors: Additional error context to include in the Problem response.

        Returns:
            A new Problem instance populated from the HTTPException.
        """
        return ProblemException(
            _type="exception:http",
            status=exc.status_code,
            detail=exc.detail,
            instance=request.url.path,
            errors=errors or [],
        )

    @staticmethod
    def as_request_validation_error(exc: RequestValidationError, request: Request) -> ProblemException:
        """
        Create a new Problem instance from a RequestValidationError.

        The Problem will take on a status code of 422 Bad Request, indicating that
        the user provided data which the server will not process. The title will
        be "Validation Error". The specifics of which fields failed validation
        checks are included as additional Problem context.

        Args:
            exc: The RequestValidationError to convert into a Problem exception.
            request: The Request object that triggered the exception.

        Returns:
             A new Problem instance populated from the RequestValidationError.
        """
        return ProblemException(
            _type="exception:validation",
            title="Validation Error",
            status=422,
            detail="One or more user-provided parameters are invalid, please see errors for details.",
            instance=request.url.path,
            errors=[err for err in exc.errors()],
        )

    @staticmethod
    def as_uncaught_exception(exc: Exception, request: Request) -> ProblemException:
        """
        Create a new Problem instance from a broad-class Exception.

        Converting a general Exception into a Problem is indicative of a server
        error, where some exception is not handled explicitly or not wrapped in
        a Problem/HTTPException.

        When creating a Problem from Exception, the Problem will always use the
        500 Server Error status code, however instead of "Server Error" as the
        title, "Unexpected Server Error" is used to indicate that an exception
        was not properly wrapped/raised.

        The exception class is provided as additional Problem context, and the
        exception message is used as Problem details.

        Args:
            exc: The general Exception to convert into a Problem exception.
            request: The Request object that triggered the exception.

        Returns:
            A new Problem instance populated from the Exception.
        """
        return ProblemException(
            _type="exception:uncaught",
            status=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Uncaught exception occurred while processing the request.",
            instance=request.url.path,
            errors=[
                ErrorLogRecord(
                    exception_type=exc.__class__.__name__,
                    exception_message=str(exc),
                    exception_stack_trace="".join(traceback.format_exception(exc.__class__, exc, exc.__traceback__)),
                ).to_dict()
            ],
        )

    @staticmethod
    def http_error_example(path=None, status_code=HTTP_404_NOT_FOUND, detail=None, errors=None) -> dict:
        return ProblemResponse.as_http_exception(
            exc=HTTPException(
                status_code=status_code,
                detail=detail or "Details for the HTTP error occurred.",
            ),
            request=documentation.request_obj(path),
            errors=errors,
        ).to_dict()

    @staticmethod
    def validation_error_example(path=None) -> dict:
        return ProblemResponse.as_request_validation_error(
            exc=RequestValidationError(
                errors=[
                    {
                        "loc": ["body", "some_type"],
                        "msg": "Input should be one of 'value_a', 'value_b', 'value_c' or 'value_d'",
                        "type": "enum",
                    },
                ]
            ),
            request=documentation.request_obj(path),
        ).to_dict()

    @staticmethod
    def exception_error_example(path=None) -> dict:
        return ProblemResponse.as_uncaught_exception(
            exc=documentation.exception_obj(), request=documentation.request_obj(path)
        ).to_dict()

    @staticmethod
    def from_domain_exception(exc: Exception, instance: str) -> Response:
        """
        Maps known exceptions to appropriate HTTP status codes,
        then returns a ProblemException (which can produce a ProblemResponse).
        """
        match exc:
            case validation_failure_error.ValidationFailureError():
                http_status = HTTP_400_BAD_REQUEST
            case not_found_error.NotFoundError():
                http_status = HTTP_404_NOT_FOUND
            case conflict_value_error.ConflictValueError():
                http_status = HTTP_409_CONFLICT
            case _:
                http_status = HTTP_500_INTERNAL_SERVER_ERROR
        return ProblemException(
            status=http_status,
            detail=str(exc),
            instance=instance,
        ).to_response()
