from fastapi import APIRouter, status
from sqlalchemy import text

from app.db.session import engine


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
def health_check() -> dict[str, str]:
    """Check API, PostgreSQL, and PostGIS availability."""

    database_status = "ok"
    postgis_status = "ok"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT PostGIS_Version()"))
    except Exception:
        postgis_status = "unavailable"

    if database_status != "ok" or postgis_status != "ok":
        return {
            "status": "degraded",
            "database": database_status,
            "postgis": postgis_status,
        }

    return {
        "status": "healthy",
        "database": database_status,
        "postgis": postgis_status,
    }