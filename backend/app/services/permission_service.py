from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.permission import Permission


def list_permissions(
    db: Session,
    *,
    search: str | None = None,
    resource: str | None = None,
    action: str | None = None,
    is_active: bool | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Permission], int]:
    """Return a filtered, paginated permission list and total count."""
    normalized_search = search.strip().lower() if search else None
    normalized_resource = resource.strip().lower() if resource else None
    normalized_action = action.strip().lower() if action else None

    conditions = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        conditions.append(
            or_(
                func.lower(Permission.code).like(search_pattern),
                func.lower(Permission.name).like(search_pattern),
                func.lower(Permission.resource).like(search_pattern),
                func.lower(Permission.action).like(search_pattern),
            )
        )

    if normalized_resource:
        conditions.append(
            func.lower(Permission.resource) == normalized_resource,
        )

    if normalized_action:
        conditions.append(
            func.lower(Permission.action) == normalized_action,
        )

    if is_active is not None:
        conditions.append(
            Permission.is_active.is_(is_active),
        )

    count_statement = select(func.count()).select_from(Permission)

    if conditions:
        count_statement = count_statement.where(*conditions)

    total = db.scalar(count_statement) or 0

    permissions_statement = (
        select(Permission)
        .where(*conditions)
        .order_by(
            Permission.resource,
            Permission.action,
            Permission.code,
            Permission.id,
        )
        .offset(offset)
        .limit(limit)
    )

    permissions = list(
        db.scalars(permissions_statement).all(),
    )

    return permissions, total


def get_permission(
    db: Session,
    permission_id: UUID,
) -> Permission | None:
    """Return a permission by UUID."""
    statement = select(Permission).where(
        Permission.id == permission_id,
    )

    return db.scalar(statement)


def create_permission(
    db: Session,
    *,
    code: str,
    name: str,
    resource: str,
    action: str,
    description: str | None = None,
    is_system_permission: bool = True,
    commit: bool = True,
) -> Permission:
    """Create a permission."""
    normalized_code = code.strip().lower()
    normalized_name = name.strip()
    normalized_resource = resource.strip().lower()
    normalized_action = action.strip().lower()
    normalized_description = (
        description.strip()
        if description is not None
        else None
    )

    if not normalized_code:
        raise ValueError("Permission code must not be empty.")

    if not normalized_name:
        raise ValueError("Permission name must not be empty.")

    if not normalized_resource:
        raise ValueError("Permission resource must not be empty.")

    if not normalized_action:
        raise ValueError("Permission action must not be empty.")

    existing_permission = db.scalar(
        select(Permission).where(
            Permission.code == normalized_code,
        )
    )

    if existing_permission is not None:
        raise ValueError(
            "A permission with this code already exists."
        )

    permission = Permission(
        code=normalized_code,
        name=normalized_name,
        resource=normalized_resource,
        action=normalized_action,
        description=normalized_description or None,
        is_system_permission=is_system_permission,
    )

    db.add(permission)

    try:
        if commit:
            db.commit()
            db.refresh(permission)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A permission with this code already exists."
        ) from None

    return permission


def update_permission(
    db: Session,
    permission_id: UUID,
    *,
    code: str,
    name: str,
    resource: str,
    action: str,
    description: str | None = None,
    commit: bool = True,
) -> Permission:
    """Update a permission's basic information."""
    permission = get_permission(
        db=db,
        permission_id=permission_id,
    )

    if permission is None:
        raise ValueError("Permission not found.")

    normalized_code = code.strip().lower()
    normalized_name = name.strip()
    normalized_resource = resource.strip().lower()
    normalized_action = action.strip().lower()
    normalized_description = (
        description.strip()
        if description is not None
        else None
    )

    if not normalized_code:
        raise ValueError("Permission code must not be empty.")

    if not normalized_name:
        raise ValueError("Permission name must not be empty.")

    if not normalized_resource:
        raise ValueError("Permission resource must not be empty.")

    if not normalized_action:
        raise ValueError("Permission action must not be empty.")

    existing_permission = db.scalar(
        select(Permission).where(
            Permission.code == normalized_code,
            Permission.id != permission_id,
        )
    )

    if existing_permission is not None:
        raise ValueError(
            "A permission with this code already exists."
        )

    permission.code = normalized_code
    permission.name = normalized_name
    permission.resource = normalized_resource
    permission.action = normalized_action
    permission.description = normalized_description or None

    try:
        if commit:
            db.commit()
            db.refresh(permission)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A permission with this code already exists."
        ) from None

    return permission


def set_permission_active_status(
    db: Session,
    permission_id: UUID,
    *,
    is_active: bool,
    commit: bool = True,
) -> Permission:
    """Activate or deactivate a permission."""
    permission = get_permission(
        db=db,
        permission_id=permission_id,
    )

    if permission is None:
        raise ValueError("Permission not found.")

    permission.is_active = is_active

    if commit:
        db.commit()
        db.refresh(permission)
    else:
        db.flush()

    return permission