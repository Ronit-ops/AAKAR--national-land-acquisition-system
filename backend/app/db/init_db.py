from sqlalchemy import text

from app.db.session import engine


def check_database_connection() -> bool:
    """Check whether the application can connect to PostgreSQL."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_postgis_connection() -> bool:
    """Check whether PostGIS is available in the database."""

    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT PostGIS_Version()")
            ).scalar_one()

        return bool(result)
    except Exception:
        return False