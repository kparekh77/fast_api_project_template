import uuid

import structlog
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI

"""
Also known as a Transit ID, is a unique identifier value that is attached to requests
and messages that allow reference to a particular transaction or event chain.

For Correlation ID, in general, you don’t have to use one. But if you are designing a
distributed system that incorporates message queues and asynchronous processing, you will
do well to include a Correlation ID in your messages.

Within HTTP headers, this is usually set as `x-correlation-id`.
"""
TRACEABILITY_ID_ATTRIBUTE: str = "correlation_id"
TRACEABILITY_ID_HTTP_HEADER: str = "x-correlation-id"


class TraceabilityMiddleware(CorrelationIdMiddleware):
    """
    Middleware to trace the system and entity of the request
    """

    def __init__(
        self,
        app: FastAPI,
        system: str = "UNKNOWN",
        entity: str = "UNKNOWN",
        header_name: str = TRACEABILITY_ID_HTTP_HEADER,
        update_request_header: bool = False,
        generator: callable = lambda: uuid.uuid4().hex,
    ) -> None:
        super().__init__(
            app=app,
            header_name=header_name,
            update_request_header=update_request_header,
            generator=generator,
        )
        self.system = system
        self.entity = entity

    async def __call__(self, scope, receive, send) -> None:
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            system=self.system,
            entity=self.entity,
        )
        await super().__call__(scope, receive, send)
        return


def get_correlation_id() -> str:
    try:
        return correlation_id.get()
    except LookupError:
        return "NONE"
