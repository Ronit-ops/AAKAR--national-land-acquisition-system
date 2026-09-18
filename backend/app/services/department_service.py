from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.department import Department


def list_departments(
    db: Session,
    *,
    search: str | None = None,
    is_active: bool | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Department], int]:
    """Return a filtered, paginated department list and total count."""
    normalized_search = search.strip().lower() if search else None

    conditions = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        conditions.append(
            or_(
                func.lower(Department.code).like(search_pattern),
                func.lower(Department.name).like(search_pattern),
            )
        )

    if is_active is not None:
        conditions.append(Department.is_active.is_(is_active))

    count_statement = select(func.count()).select_from(Department)

    if conditions:
        count_statement = count_statement.where(*conditions)

    total = db.scalar(count_statement) or 0

    departments_statement = (
        select(Department)
        .where(*conditions)
        .order_by(
            Department.name,
            Department.id,
        )
        .offset(offset)
        .limit(limit)
    )

    departments = list(
        db.scalars(departments_statement).all(),
    )

    return departments, total


def get_department(
    db: Session,
    department_id: UUID,
) -> Department | None:
    """Return a department by UUID."""
    statement = select(Department).where(
        Department.id == department_id,
    )

    return db.scalar(statement)


def create_department(
    db: Session,
    *,
    code: str,
    name: str,
    description: str | None = None,
    commit: bool = True,
) -> Department:
    """Create a department."""
    normalized_code = code.strip().upper()
    normalized_name = name.strip()
    normalized_description = (
        description.strip()
        if description is not None
        else None
    )

    if not normalized_code:
        raise ValueError("Department code must not be empty.")

    if not normalized_name:
        raise ValueError("Department name must not be empty.")

    existing_department = db.scalar(
        select(Department).where(
            Department.code == normalized_code,
        )
    )

    if existing_department is not None:
        raise ValueError(
            "A department with this code already exists."
        )

    department = Department(
        code=normalized_code,
        name=normalized_name,
        description=normalized_description or None,
    )

    db.add(department)

    try:
        if commit:
            db.commit()
            db.refresh(department)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A department with this code already exists."
        ) from None

    return department


def update_department(
    db: Session,
    department_id: UUID,
    *,
    code: str,
    name: str,
    description: str | None = None,
    commit: bool = True,
) -> Department:
    """Update a department's basic information."""
    department = get_department(
        db=db,
        department_id=department_id,
    )

    if department is None:
        raise ValueError("Department not found.")

    normalized_code = code.strip().upper()
    normalized_name = name.strip()
    normalized_description = (
        description.strip()
        if description is not None
        else None
    )

    if not normalized_code:
        raise ValueError("Department code must not be empty.")

    if not normalized_name:
        raise ValueError("Department name must not be empty.")

    existing_department = db.scalar(
        select(Department).where(
            Department.code == normalized_code,
            Department.id != department_id,
        )
    )

    if existing_department is not None:
        raise ValueError(
            "A department with this code already exists."
        )

    department.code = normalized_code
    department.name = normalized_name
    department.description = normalized_description or None

    try:
        if commit:
            db.commit()
            db.refresh(department)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A department with this code already exists."
        ) from None

    return department


def set_department_active_status(
    db: Session,
    department_id: UUID,
    *,
    is_active: bool,
    commit: bool = True,
) -> Department:
    """Activate or deactivate a department."""
    department = get_department(
        db=db,
        department_id=department_id,
    )

    if department is None:
        raise ValueError("Department not found.")

    department.is_active = is_active

    if commit:
        db.commit()
        db.refresh(department)
    else:
        db.flush()

    return department
