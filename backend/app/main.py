from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging


setup_logging()
logger = get_logger(__name__)


allowed_origins = [
    origin.strip()
    for origin in settings.cors_allowed_origins.split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    logger.info("Starting %s application", settings.app_name)
    logger.info("Environment: %s", settings.app_env)
    yield
    logger.info("Shutting down %s application", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="National Land Acquisition & Management System",
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
    ],
)


app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get("/")
def root() -> dict[str, str]:
    """Basic application endpoint."""
    return {
        "application": settings.app_name,
        "status": "running",
        "version": "0.1.0",
    }