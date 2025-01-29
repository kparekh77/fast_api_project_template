import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from config.config_map_loader import KillSwitchConfig
from model.problem.exception import ProblemException


class KillSwitchMiddleware(BaseHTTPMiddleware):
    """
    Middleware to return a 503 Service Unavailable response when the service is disabled.
    """

    def __init__(self, app: FastAPI, logger: logging.Logger, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
        self._logger = logger

    async def dispatch(self, request: Request, call_next):
        normalised_path = request.url.path.rstrip("/")
        normalised_exclude_paths = [path.rstrip("/") for path in self.exclude_paths]
        if normalised_path in normalised_exclude_paths:
            return await call_next(request)
        else:
            if KillSwitchConfig.load().enabled:
                message = "Kill-Switch is enabled. Please contact the service owner for more information."
                self._logger.warning(message)
                return ProblemException(
                    status=HTTPStatus.SERVICE_UNAVAILABLE,
                    detail=message,
                ).to_response()
            else:
                response = await call_next(request)
                return response
