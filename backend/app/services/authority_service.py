from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.authority import Authority
from app.models.department import Department


VALID_AUTHORITY_TYPES = {
    "CENTRAL",
    "STATE",
    "DISTRICT",
    "OTHER",
}


def list_authorities(
    db: Session,
    *,
    search: str | None = None,
    department_id: UUID | None = None,
    authority_type: str | None = None,
    is_active: bool | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Authority], int]:
    """Return a filtered, paginated authority list and total count."""
    normalized_search = search.strip().lower() if search else None
    normalized_type = authority_type.strip().upper() if authority_type else None

    conditions = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        conditions.append(
            or_(
                func.lower(Authority.code).like(search_pattern),
                func.lower(Authority.name).like(search_pattern),
            )
        )

    if department_id is not None:
        conditions.append(Authority.department_id == department_id)

    if normalized_type:
        if normalized_type not in VALID_AUTHORITY_TYPES:
            raise ValueError("Invalid authority type.")

        conditions.append(Authority.authority_type == normalized_type)

    if is_active is not None:
        conditions.append(Authority.is_active.is_(is_active))

    count_statement = select(func.count()).select_from(Authority)

    if conditions:
        count_statement = count_statement.where(*conditions)

    total = db.scalar(count_statement) or 0

    authorities_statement = (
        select(Authority)
        .where(*conditions)
        .order_by(
            Authority.name,
            Authority.id,
        )
        .offset(offset)
        .limit(limit)
    )

    authorities = list(
        db.scalars(authorities_statement).all(),
    )

    return authorities, total


def get_authority(
    db: Session,
    authority_id: UUID,
) -> Authority | None:
    """Return an authority by UUID."""
    statement = select(Authority).where(
        Authority.id == authority_id,
    )

    return db.scalar(statement)


def create_authority(
    db: Session,
    *,
    department_id: UUID,
    code: str,
    name: str,
    authority_type: str,
    description: str | None = None,
    commit: bool = True,
) -> Authority:
    """Create an authority under an active department."""
    department = db.get(Department, department_id)

    if department is None:
        raise ValueError("Department not found.")

    if not department.is_active:
        raise ValueError("Cannot create an authority under an inactive department.")

    normalized_code = code.strip().upper()
    normalized_name = name.strip()
    normalized_type = authority_type.strip().upper()
    normalized_description = (
        description.strip()
        if description is not None
        else None
    )

    if not normalized_code:
        raise ValueError("Authority code must not be empty.")

    if not normalized_name:
        raise ValueError("Authority name must not be empty.")

    if normalized_type not in VALID_AUTHORITY_TYPES:
        raise ValueError("Invalid authority type.")

    existing_authority = db.scalar(
        select(Authority).where(
            Authority.code == normalized_code,
        )
    )

    if existing_authority is not None:
        raise ValueError(
            "An authority with this code already exists."
        )

    authority = Authority(
        department_id=department_id,
        code=normalized_code,
        name=normalized_name,
        authority_type=normalized_type,
        description=normalized_description or None,
    )

    db.add(authority)

    try:
        if commit:
            db.commit()
            db.refresh(authority)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "An authority with this code already exists."
        ) from None

    return authority


def update_authority(
    db: Session,
    authority_id: UUID,
    *,
    department_id: UUID,
    code: str,
    name: str,
    authority_type: str,
    description: str | None = None,
    commit: bool = True,
) -> Authority:
    """Update an authority's organizational information."""
    authority = get_authority(
        db=db,
        authority_id=authority_id,
    )

    if authority is None:
        raise ValueError("Authority not found.")

    department = db.get(Department, department_id)

    if department is None:
        raise ValueError("Department not found.")

    if not department.is_active:
        raise ValueError("Cannot assign an authority to an inactive department.")

    normalized_code = code.strip().upper()
    normalized_name = name.strip()
    normalized_type = authority_type.strip().upper()
    normalized_description = (
        description.strip()
        if description is not None
        else None
    )

    if not normalized_code:
        raise ValueError("Authority code must not be empty.")

    if not normalized_name:
        raise ValueError("Authority name must not be empty.")

    if normalized_type not in VALID_AUTHORITY_TYPES:
        raise ValueError("Invalid authority type.")

    existing_authority = db.scalar(
        select(Authority).where(
            Authority.code == normalized_code,
            Authority.id != authority_id,
        )
    )

    if existing_authority is not None:
        raise ValueError(
            "An authority with this code already exists."
        )

    authority.department_id = department_id
    authority.code = normalized_code
    authority.name = normalized_name
    authority.authority_type = normalized_type
    authority.description = normalized_description or None

    try:
        if commit:
            db.commit()
            db.refresh(authority)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "An authority with this code already exists."
        ) from None

    return authority


def set_authority_active_status(
    db: Session,
    authority_id: UUID,
    *,
    is_active: bool,
    commit: bool = True,
) -> Authority:
    """Activate or deactivate an authority."""
    authority = get_authority(
        db=db,
        authority_id=authority_id,
    )

    if authority is None:
        raise ValueError("Authority not found.")

    authority.is_active = is_active

    if commit:
        db.commit()
        db.refresh(authority)
    else:
        db.flush()

    return authority
