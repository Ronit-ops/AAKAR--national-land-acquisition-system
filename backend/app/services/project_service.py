from __future__ import annotations

from typing import Any
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.authority import Authority
from app.models.project import Project
from app.services.audit_service import record_audit_event


PROJECT_STATUS_DRAFT = "DRAFT"
PROJECT_STATUS_ACTIVE = "ACTIVE"
PROJECT_STATUS_CLOSED = "CLOSED"

PROJECT_STATUSES = {
    PROJECT_STATUS_DRAFT,
    PROJECT_STATUS_ACTIVE,
    PROJECT_STATUS_CLOSED,
}


def _normalize_text(value: str) -> str:
    return value.strip()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _validate_project_status(status: str) -> None:
    if status not in PROJECT_STATUSES:
        raise ValueError("Invalid project status.")


def _validate_authority(
    db: Session,
    authority_id: UUID,
) -> Authority:
    authority = db.get(Authority, authority_id)

    if authority is None:
        raise ValueError("Responsible authority not found.")

    if not authority.is_active:
        raise ValueError(
            "Cannot assign a project to an inactive authority."
        )

    return authority


def _validate_geojson_geometry(
    boundary: dict[str, Any] | None,
) -> str | None:
    """
    Validate a GeoJSON Polygon or MultiPolygon and convert it to WKT.

    A project boundary is stored as PostGIS MULTIPOLYGON geometry.
    Polygon input is accepted and normalized into a MULTIPOLYGON.
    """

    if boundary is None:
        return None

    if not isinstance(boundary, dict):
        raise ValueError("Project boundary must be a GeoJSON object.")

    boundary_type = boundary.get("type")
    coordinates = boundary.get("coordinates")

    if boundary_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(
            "Project boundary must be a GeoJSON Polygon or MultiPolygon."
        )

    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("Project boundary coordinates are required.")

    if boundary_type == "Polygon":
        polygons = [coordinates]
    else:
        polygons = coordinates

    if not polygons:
        raise ValueError("Project boundary must contain at least one polygon.")

    polygon_wkts: list[str] = []

    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError(
                "Each project polygon must contain at least one ring."
            )

        ring_wkts: list[str] = []

        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4:
                raise ValueError(
                    "Each project boundary ring must contain at least "
                    "four coordinate positions."
                )

            points: list[str] = []

            for position in ring:
                if (
                    not isinstance(position, list)
                    or len(position) < 2
                ):
                    raise ValueError(
                        "Each project boundary coordinate must contain "
                        "longitude and latitude."
                    )

                longitude = position[0]
                latitude = position[1]

                if not isinstance(longitude, (int, float)):
                    raise ValueError(
                        "Project boundary longitude must be numeric."
                    )

                if not isinstance(latitude, (int, float)):
                    raise ValueError(
                        "Project boundary latitude must be numeric."
                    )

                if not -180 <= longitude <= 180:
                    raise ValueError(
                        "Project boundary longitude must be between "
                        "-180 and 180."
                    )

                if not -90 <= latitude <= 90:
                    raise ValueError(
                        "Project boundary latitude must be between "
                        "-90 and 90."
                    )

                points.append(f"{longitude} {latitude}")

            if points[0] != points[-1]:
                raise ValueError(
                    "Project boundary rings must be closed."
                )

            ring_wkts.append(f"({', '.join(points)})")

        polygon_wkts.append(
            f"({', '.join(ring_wkts)})"
        )

    return f"MULTIPOLYGON({', '.join(polygon_wkts)})"


def _build_boundary(
    boundary: dict[str, Any] | None,
) -> WKTElement | None:
    wkt = _validate_geojson_geometry(boundary)

    if wkt is None:
        return None

    return WKTElement(wkt, srid=4326)


def _ensure_unique_project_code(
    db: Session,
    code: str,
    exclude_project_id: UUID | None = None,
) -> None:
    statement = select(Project.id).where(
        func.lower(Project.code) == code.lower()
    )

    if exclude_project_id is not None:
        statement = statement.where(
            Project.id != exclude_project_id
        )

    existing_project_id = db.scalar(statement)

    if existing_project_id is not None:
        raise ValueError(
            "A project with this code already exists."
        )


def list_projects(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    responsible_authority_id: UUID | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Project], int]:
    normalized_search = _normalize_optional_text(search)

    if status is not None:
        status = status.strip().upper()
        _validate_project_status(status)

    if offset < 0:
        raise ValueError("Offset cannot be negative.")

    if limit < 1 or limit > 100:
        raise ValueError(
            "Limit must be between 1 and 100."
        )

    conditions = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        conditions.append(
            or_(
                Project.code.ilike(search_pattern),
                Project.name.ilike(search_pattern),
                Project.sector.ilike(search_pattern),
            )
        )

    if status is not None:
        conditions.append(Project.status == status)

    if responsible_authority_id is not None:
        conditions.append(
            Project.responsible_authority_id
            == responsible_authority_id
        )

    count_statement = select(func.count(Project.id))

    if conditions:
        count_statement = count_statement.where(*conditions)

    total = db.scalar(count_statement) or 0

    statement = (
        select(Project)
        .order_by(
            Project.created_at.desc(),
            Project.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    if conditions:
        statement = statement.where(*conditions)

    projects = list(db.scalars(statement).all())

    return projects, total


def get_project(
    db: Session,
    project_id: UUID,
) -> Project | None:
    return db.get(Project, project_id)


def create_project(
    db: Session,
    *,
    code: str,
    name: str,
    sector: str,
    description: str | None,
    responsible_authority_id: UUID,
    boundary: dict[str, Any] | None,
    actor_user_id: UUID,
) -> Project:
    normalized_code = _normalize_text(code)
    normalized_name = _normalize_text(name)
    normalized_sector = _normalize_text(sector)
    normalized_description = _normalize_optional_text(description)

    if not normalized_code:
        raise ValueError("Project code cannot be empty.")

    if not normalized_name:
        raise ValueError("Project name cannot be empty.")

    if not normalized_sector:
        raise ValueError("Project sector cannot be empty.")

    _ensure_unique_project_code(
        db,
        normalized_code,
    )

    _validate_authority(
        db,
        responsible_authority_id,
    )

    boundary_geometry = _build_boundary(boundary)

    project = Project(
        code=normalized_code,
        name=normalized_name,
        sector=normalized_sector,
        description=normalized_description,
        responsible_authority_id=responsible_authority_id,
        boundary=boundary_geometry,
        status=PROJECT_STATUS_DRAFT,
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )

    db.add(project)

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="project_created",
            entity_type="project",
            entity_id=project.id,
            result="success",
            details={
                "code": project.code,
                "name": project.name,
                "status": project.status,
            },
            commit=False,
        )

        db.commit()
        db.refresh(project)

        return project

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to create project because the project "
            "violates a database constraint."
        ) from exc

    except Exception:
        db.rollback()
        raise


def update_project(
    db: Session,
    *,
    project_id: UUID,
    code: str,
    name: str,
    sector: str,
    description: str | None,
    responsible_authority_id: UUID,
    boundary: dict[str, Any] | None,
    actor_user_id: UUID,
) -> Project:
    project = db.get(Project, project_id)

    if project is None:
        raise ValueError("Project not found.")

    if project.status == PROJECT_STATUS_CLOSED:
        raise ValueError(
            "Closed projects cannot be updated."
        )

    normalized_code = _normalize_text(code)
    normalized_name = _normalize_text(name)
    normalized_sector = _normalize_text(sector)
    normalized_description = _normalize_optional_text(description)

    if not normalized_code:
        raise ValueError("Project code cannot be empty.")

    if not normalized_name:
        raise ValueError("Project name cannot be empty.")

    if not normalized_sector:
        raise ValueError("Project sector cannot be empty.")

    _ensure_unique_project_code(
        db,
        normalized_code,
        exclude_project_id=project.id,
    )

    _validate_authority(
        db,
        responsible_authority_id,
    )

    boundary_geometry = _build_boundary(boundary)

    project.code = normalized_code
    project.name = normalized_name
    project.sector = normalized_sector
    project.description = normalized_description
    project.responsible_authority_id = responsible_authority_id
    project.boundary = boundary_geometry
    project.updated_by_user_id = actor_user_id

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="project_updated",
            entity_type="project",
            entity_id=project.id,
            result="success",
            details={
                "code": project.code,
                "name": project.name,
                "status": project.status,
            },
            commit=False,
        )

        db.commit()
        db.refresh(project)

        return project

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to update project because the project "
            "violates a database constraint."
        ) from exc

    except Exception:
        db.rollback()
        raise


def activate_project(
    db: Session,
    *,
    project_id: UUID,
    actor_user_id: UUID,
) -> Project:
    project = db.get(Project, project_id)

    if project is None:
        raise ValueError("Project not found.")

    if project.status != PROJECT_STATUS_DRAFT:
        raise ValueError(
            "Only draft projects can be activated."
        )

    project.status = PROJECT_STATUS_ACTIVE
    project.updated_by_user_id = actor_user_id

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="project_activated",
            entity_type="project",
            entity_id=project.id,
            result="success",
            details={
                "previous_status": PROJECT_STATUS_DRAFT,
                "new_status": PROJECT_STATUS_ACTIVE,
            },
            commit=False,
        )

        db.commit()
        db.refresh(project)

        return project

    except Exception:
        db.rollback()
        raise


def close_project(
    db: Session,
    *,
    project_id: UUID,
    actor_user_id: UUID,
) -> Project:
    project = db.get(Project, project_id)

    if project is None:
        raise ValueError("Project not found.")

    if project.status != PROJECT_STATUS_ACTIVE:
        raise ValueError(
            "Only active projects can be closed."
        )

    project.status = PROJECT_STATUS_CLOSED
    project.updated_by_user_id = actor_user_id

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="project_closed",
            entity_type="project",
            entity_id=project.id,
            result="success",
            details={
                "previous_status": PROJECT_STATUS_ACTIVE,
                "new_status": PROJECT_STATUS_CLOSED,
            },
            commit=False,
        )

        db.commit()
        db.refresh(project)

        return project

    except Exception:
        db.rollback()
        raise