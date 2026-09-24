from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.projects import (
    CreateProjectRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatusResponse,
    UpdateProjectRequest,
)
from app.services.project_service import (
    activate_project,
    close_project,
    create_project,
    get_project,
    list_projects,
    update_project,
)


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


def _project_response(project) -> ProjectResponse:
    """Convert a Project model into the public API response."""
    boundary = None

    if project.boundary is not None:
        try:
            from geoalchemy2.shape import to_shape

            geometry = to_shape(project.boundary)

            if geometry.geom_type == "Polygon":
                rings = [
                    [
                        [x, y]
                        for x, y in geometry.exterior.coords
                    ]
                ]

                for interior in geometry.interiors:
                    rings.append(
                        [
                            [x, y]
                            for x, y in interior.coords
                        ]
                    )

                boundary = {
                    "type": "Polygon",
                    "coordinates": rings,
                }

            elif geometry.geom_type == "MultiPolygon":
                polygons = []

                for polygon in geometry.geoms:
                    rings = [
                        [
                            [x, y]
                            for x, y in polygon.exterior.coords
                        ]
                    ]

                    for interior in polygon.interiors:
                        rings.append(
                            [
                                [x, y]
                                for x, y in interior.coords
                            ]
                        )

                    polygons.append(rings)

                boundary = {
                    "type": "MultiPolygon",
                    "coordinates": polygons,
                }

        except Exception:
            boundary = None

    return ProjectResponse(
        id=project.id,
        code=project.code,
        name=project.name,
        sector=project.sector,
        description=project.description,
        responsible_authority_id=project.responsible_authority_id,
        boundary=boundary,
        status=project.status,
        created_by_user_id=project.created_by_user_id,
        updated_by_user_id=project.updated_by_user_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
)
def list_project_records(
    search: str | None = Query(
        default=None,
        max_length=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("project.read")),
):
    """List and search projects."""
    try:
        projects, total = list_projects(
            db=db,
            search=search,
            offset=offset,
            limit=limit,
        )

        return ProjectListResponse(
            items=[
                _project_response(project)
                for project in projects
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def get_project_record(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("project.read")),
):
    """Return a project by ID."""
    project = get_project(
        db=db,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    return _project_response(project)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_record(
    payload: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("project.create")),
):
    """Create a new project in DRAFT status."""
    try:
        project = create_project(
            db=db,
            code=payload.code,
            name=payload.name,
            sector=payload.sector,
            description=payload.description,
            responsible_authority_id=payload.responsible_authority_id,
            boundary=payload.boundary,
            actor_user_id=current_user.id,
        )

        return _project_response(project)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Project could not be created because "
                "of a conflicting record."
            ),
        ) from exc


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
)
def update_project_record(
    project_id: UUID,
    payload: UpdateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("project.update")),
):
    """Update editable project information."""
    try:
        project = update_project(
            db=db,
            project_id=project_id,
            code=payload.code,
            name=payload.name,
            sector=payload.sector,
            description=payload.description,
            responsible_authority_id=payload.responsible_authority_id,
            boundary=payload.boundary,
            actor_user_id=current_user.id,
        )

        return _project_response(project)

    except ValueError as exc:
        message = str(exc)

        if message == "Project not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        if "already exists" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Project could not be updated because "
                "of a conflicting record."
            ),
        ) from exc


@router.post(
    "/{project_id}/activate",
    response_model=ProjectStatusResponse,
    status_code=status.HTTP_200_OK,
)
def activate_project_record(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("project.activate")),
):
    """Transition a project from DRAFT to ACTIVE."""
    try:
        project = activate_project(
            db=db,
            project_id=project_id,
            actor_user_id=current_user.id,
        )

        return ProjectStatusResponse(
            id=project.id,
            status=project.status,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Project not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Project status could not be changed because "
                "of a conflicting record."
            ),
        ) from exc


@router.post(
    "/{project_id}/close",
    response_model=ProjectStatusResponse,
    status_code=status.HTTP_200_OK,
)
def close_project_record(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("project.close")),
):
    """Transition a project from ACTIVE to CLOSED."""
    try:
        project = close_project(
            db=db,
            project_id=project_id,
            actor_user_id=current_user.id,
        )

        return ProjectStatusResponse(
            id=project.id,
            status=project.status,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Project not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Project status could not be changed because "
                "of a conflicting record."
            ),
        ) from exc