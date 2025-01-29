import logging
import time
import uuid

import structlog
from fastapi import FastAPI
from starlette.concurrency import iterate_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config.logging_configurator import HttpLogRecord
from middleware.traceability_middleware import get_correlation_id

"""
Uniquely identifies & couples every request/response received/sent by the application.
This is generated within the call-site and the header is passed within the response.

In the event that the request already contains a request ID, it will be used as
some systems may be using it as a traceability ID.

Within HTTP headers, this is usually set as `x-request-id`.
"""
REQUEST_ID_ATTRIBUTE: str = "request_id"
REQUEST_ID_HTTP_HEADER: str = "x-request-id"

"""
The source of the request. This is used to identify the source/system of the request.
"""
SOURCE_HTTP_HEADER: str = "x-source"


class HttpLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log useful HTTP requests and responses attributes.
    """

    def __init__(
        self,
        app: FastAPI,
        logger: logging.Logger,
        exclude_paths: list[str] = None,
    ) -> None:
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self._logger = logger

    async def dispatch(self, request: Request, call_next) -> Response:
        normalised_path = request.url.path.rstrip("/")
        normalised_exclude_paths = [path.rstrip("/") for path in self.exclude_paths]
        if normalised_path in normalised_exclude_paths:
            return await call_next(request)
        else:
            start_time = time.perf_counter_ns()
            structlog.contextvars.bind_contextvars(correlation_id=get_correlation_id())

            request_id = request.headers.get(REQUEST_ID_HTTP_HEADER, uuid.uuid4().hex)

            try:
                request_body = str(await request.body())
            except Exception:
                request_body = ""

            self._logger.info(
                msg="INCOMING REQUEST", extra=HttpLogRecord.request_attribute(request, request_id, request_body)
            )

            response: Response = await call_next(request)
            response_duration_ms = int((time.perf_counter_ns() - start_time) / 1_000_000)
            response.headers[REQUEST_ID_HTTP_HEADER] = request_id

            response_body: str = ""
            if hasattr(response, "body_iterator"):
                response_body_merge = [chunk async for chunk in response.body_iterator]
                response.body_iterator = iterate_in_threadpool(iter(response_body_merge))
                if len(response_body_merge) > 0:
                    response_body = response_body_merge[0].decode()

            self._logger.info(
                msg="OUTGOING RESPONSE",
                extra=HttpLogRecord.response_attribute(response, response_duration_ms, response_body),
            )

            return response
