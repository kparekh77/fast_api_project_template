from contextlib import asynccontextmanager

import logging_http_client
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logging_http_client import LoggingHttpClient
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic.v1 import parse_obj_as
from repository.config import engine_configurator

from config import environment_loader, logging_configurator, problem_configurator
from config.environment_loader import Environment
from endpoints.generic_endpoint import router as generic_router
from endpoints.liveness_endpoint import router as liveness_router
from endpoints.readiness_endpoint import router as readiness_router
from middleware import traceability_middleware
from middleware.http_logging_middleware import HttpLoggingMiddleware
from middleware.kill_switch_middleware import KillSwitchMiddleware
from middleware.traceability_middleware import TraceabilityMiddleware

# Load our environment variables (see our .env files) (MUST BE PLACED AT THE TOP)
environment_loader.init()
# Load our structured logging configuration
_logger = logging_configurator.init()

_logger.info(f"Initialising: {Environment.APP_NAME.get()}")
_logger.info(f"Version: {Environment.APP_VERSION.get()}")
_logger.info(f"Environment: {Environment.NAME.get()}")


# Lifecycle management for FastAPI is now done with async context managers
# See: https://fastapi.tiangolo.com/advanced/events/#lifespan
@asynccontextmanager
async def lifespan(entrypoint: FastAPI):
    instrumentator.expose(entrypoint, summary="Provides metrics for Prometheus.")
    yield


# Create a FastAPI instance
# See: https://fastapi.tiangolo.com/reference/fastapi/
app = FastAPI(
    lifespan=lifespan,
    title=Environment.APP_NAME.get(),
    version=Environment.APP_VERSION.get(),
    summary=Environment.APP_SUMMARY.get(),
    description=Environment.APP_DESCRIPTION.get(),
    contact={
        "name": Environment.APP_CONTACT_NAME.get(),
        "url": Environment.APP_CONTACT_URL.get(),
        "email": Environment.APP_CONTACT_EMAIL.get(),
    },
    license_info={
        "name": Environment.APP_LICENCE_NAME.get(),
        "url": Environment.APP_LICENCE_URL.get(),
    },
    openapi_tags=[], # Add tags to the OpenAPI schema
    openapi_version=Environment.OPENAPI_VERSION.get(),
)

# noinspection PyTypeChecker
# See: https://fastapi.tiangolo.com/advanced/middleware/
# Add a logging middleware to automatically log requests and responses
app.add_middleware(
    KillSwitchMiddleware,
    logger=_logger,
    exclude_paths=[
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)

# noinspection PyTypeChecker
# See: https://fastapi.tiangolo.com/advanced/middleware/
# Add a logging middleware to automatically log requests and responses
app.add_middleware(
    HttpLoggingMiddleware,
    logger=_logger,
    exclude_paths=[
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)

# noinspection PyTypeChecker
# See: https://github.com/tiangolo/fastapi/discussions/10968
# Add CORS Middleware to allow Cross-Origin Resource Sharing
# For frontend applications to access the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=Environment.APP_WEB_CORS_ALLOW_ORIGINS.get().split(","),
    allow_credentials=parse_obj_as(bool, Environment.APP_WEB_CORS_ALLOW_CREDENTIALS.get()),
    allow_methods=Environment.APP_WEB_CORS_ALLOW_METHODS.get().split(","),
    allow_headers=Environment.APP_WEB_CORS_ALLOW_HEADERS.get().split(","),
)

# Register the FastAPI RFC7807 problem middlewares
problem_configurator.init(app)

# noinspection PyTypeChecker
# See: https://github.com/tiangolo/fastapi/discussions/10968
# Add a correlation ID middleware to track the entire request/response lifecycle
app.add_middleware(
    TraceabilityMiddleware,
    system="system",
    entity=Environment.APP_NAME.get().replace(" ", "-").upper(),
)

# Instrument FastAPI with Prometheus
# See: https://github.com/trallnag/prometheus-fastapi-instrumentator
instrumentator = Instrumentator().instrument(app)

# Instantiate a Logging HTTP Client
Logging_http_client = LoggingHttpClient(
    logger=_logger,
    reusable_session=True,
    source=Environment.APP_NAME.get(),
)
logging_http_client.enable_request_body_logging()
logging_http_client.enable_response_body_logging()
logging_http_client.set_correlation_id_provider(traceability_middleware.get_correlation_id)

# Initialise the database engine
engine_configurator.init_engine(
    connection=Environment.DB_CONNECTION.get(),
    username=Environment.DB_USERNAME.get(),
    database=Environment.DB_NAME.get(),
)

# Enabled Routes
app.include_router(liveness_router)
app.include_router(readiness_router)
app.include_router(generic_router)