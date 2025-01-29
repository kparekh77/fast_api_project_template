import logging
import sys
import traceback
from dataclasses import dataclass, asdict
from typing import Dict, Union, Any

import structlog
from pydantic.v1 import parse_obj_as
from starlette.requests import Request
from starlette.responses import Response
from structlog.types import Processor
from structlog.typing import EventDict

import middleware.traceability_middleware
from config.environment_loader import Environment

LOGGER_NAME = "FWP"


def init(
    json_logs: bool = None,
    log_level: str = None,
) -> logging.Logger:
    """
    Configure our project's logging system to use a structured logging framework (structlog)
    and enable support, log processing, exception logging, and JSON logs.
    """
    if json_logs is None:
        json_logs = parse_obj_as(bool, Environment.LOG_JSON_FORMAT.get())
    if log_level is None:
        log_level = Environment.LOG_LEVEL.get()

    def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
        """
        Uvicorn logs the message a second time in the extra `color_message`, but we don't
        need it. This processor drops the key from the event dict if it exists.
        """
        event_dict.pop("color_message", None)
        return event_dict

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        timestamper,
        HttpLogRecord.processor,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:

        def rename_event_key_to_message(_, __, event_dict: EventDict) -> EventDict:
            """
            Structlog entries keep the text message in the `event` field, but our
            logging standards and attributes expect the message to be in the `message`

            This processor moves the value from one field to the other when
            logging in JSON format as the ConsoleRenderer expects the message
            to be in the `event` field, so we only rename it for JSON logs.
            """
            event_dict["message"] = event_dict.pop("event")
            return event_dict

        shared_processors.append(rename_event_key_to_message)

        # We also want to custom format the exceptions only for JSON logs, as we want to pretty-print
        # them when using the ConsoleRenderer. For that we use our own custom exception formatter.
        shared_processors.append(ErrorLogRecord.processor)

    structlog.configure(
        processors=shared_processors
        + [
            # Prepare event dict for `ProcessorFormatter`.
            # This should be the last processor in the chain.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    def append_correlation_id_if_missing(_, __, event_dict):
        if "correlation_id" not in event_dict:
            event_dict["correlation_id"] = middleware.traceability_middleware.get_correlation_id()
        return event_dict

    shared_processors.append(append_correlation_id_if_missing)

    formatter = structlog.stdlib.ProcessorFormatter(
        # These run ONLY on `logging` entries that do NOT originate within structlog.
        foreign_pre_chain=shared_processors,
        # These run on ALL entries after the pre_chain is done.
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            # Use the JSONRenderer if we're logging in JSON format (Production) or the ConsoleRenderer otherwise.
            structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer(),
        ],
    )

    # Setup the stream handler with the structured formatter
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Inject our stream handler to the root logger
    # and set the log level to the one defined in the environment.
    root_logger = logging.getLogger()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(log_level.upper())

    def configure_uvicorn_logging():
        """
        We clear the log handlers for uvicorn loggers, and enable propagation
        so the messages are caught by our root logger and formatted correctly.

        For the access logs, we clear the handlers and prevent the logs to propagate
        as we will re-create the access logs ourselves to add all information in the
        structured log (see the logging middleware).

        NOTE: One confusing thing with Uvicorn is that "uvicorn.error" is used for
              non-error logs such as server, http, and web-socket logging...
              see: https://github.com/encode/uvicorn/issues/562
        """
        for name in ["uvicorn", "uvicorn.error", "uvicorn.asgi"]:
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.propagate = True

        access_logger = logging.getLogger("uvicorn.access")
        access_logger.handlers.clear()
        access_logger.propagate = False
        access_logger.disabled = True

    """
    We re-config/disable the opinionated uvicorn logging configuration
    to inherit our own structured logging configuration.
    """
    configure_uvicorn_logging()

    def handle_exception(exc_type, exc_value, exc_traceback):
        """
        Log any uncaught exception instead of letting it be printed by Python
        (but leave KeyboardInterrupt untouched to allow users to Ctrl+C to stop)
        See https://stackoverflow.com/a/16993115/3641865
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        root_logger.error("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    return root_logger


"""
A primitive is a data type that is not an object and has no methods.

This is useful for type hinting when you want to guide the user to use primitive types only for a variable.
"""
Primitive = Union[int, float, str, bool]


@dataclass
class BaseLogRecord:
    """
    A base class for all custom log record extensions.
    """

    def to_dict(self) -> Dict[str, Primitive]:
        to_dict_cleaned = {k: v for k, v in asdict(self).items() if v not in (None, {}, [], "", 0, 0.0)}
        return to_dict_cleaned


@dataclass
class HttpLogRecord(BaseLogRecord):
    request_id: str = ""
    request_source: str = "UNKNOWN"
    request_method: str = ""
    request_url: str = ""
    request_query_params: Dict[str, Any] = None
    request_headers: Dict[str, Any] = None
    request_body: str = ""
    response_status: int = 0
    response_headers: Dict[str, Any] = None
    response_body: str = ""
    response_duration_ms: int = 0

    @staticmethod
    def request_attribute(request: Any, request_id: str, request_body: str) -> Dict:
        return {
            "_request": request,
            "_request_id": request_id,
            "_request_body": request_body,
        }

    @staticmethod
    def response_attribute(response: Any, response_duration_ms: int, response_body: str) -> Dict:
        return {
            "_response": response,
            "_response_duration_ms": response_duration_ms,
            "_response_body": response_body,
        }

    @staticmethod
    def processor(_: logging.Logger, __: str, event_dict: EventDict):
        """
        This is a structlog processor that will take the extra _request and/or _response
        attributes, break them down to HttpLogRecord attributes, and remove the _request
        and _response keys from the event dict.
        """

        request = event_dict.pop("_request", None)
        request_body = event_dict.pop("_request_body", None)
        response = event_dict.pop("_response", None)
        response_body = event_dict.pop("_response_body", None)

        if request or response:

            record = HttpLogRecord()

            if request and isinstance(request, Request):
                record.request_id = event_dict.pop("_request_id", None)
                record.request_source = request.headers.get("x-source", record.request_source)
                record.request_method = request.method
                record.request_url = str(request.url)
                record.request_query_params = dict(request.query_params) if request.query_params else {}
                record.request_headers = dict(request.headers) if request.headers else {}
                record.request_body = request_body
            if response and isinstance(response, Response):
                record.request_id = response.headers.get("x-request-id", record.request_id)
                record.response_status = response.status_code
                record.response_headers = dict(response.headers) if response.headers else {}
                record.response_body = response_body
                record.response_duration_ms = event_dict.pop("_response_duration_ms", 0)

            event_dict["http"] = record.to_dict()

        return event_dict


@dataclass
class ErrorLogRecord(BaseLogRecord):
    exception_type: str = ""
    exception_message: str = ""
    exception_stack_trace: str = ""

    @staticmethod
    def processor(_: logging.Logger, __: str, event_dict: EventDict):
        """
        This is a structlog processor that will take the extra _request and/or _response
        attributes, break them down to HttpLogRecord attributes, and remove the _request
        and _response keys from the event dict.
        """

        exc_info = event_dict.get("exc_info", None)

        if exc_info is not None and len(exc_info) == 3:
            exc_class, exc_object, exc_traceback = exc_info
            record = ErrorLogRecord(
                exception_type=exc_class.__name__,
                exception_message=str(exc_object),
                exception_stack_trace="".join(traceback.format_exception(exc_class, exc_object, exc_traceback)),
            )

            event_dict.pop("exc_info", None)
            event_dict["error"] = record.to_dict()

        return event_dict


def logger(name=LOGGER_NAME) -> logging.Logger:
    """
    A factory function that returns a logger instance with the given name.

    This is used incase want to refactor the logger instance creation in the future.
    """
    return logging.getLogger(name)
