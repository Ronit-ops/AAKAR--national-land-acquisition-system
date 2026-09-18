from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def get_role_by_code(
    db: Session,
    role_code: str,
) -> Role | None:
    """Return an active role by its normalized machine-readable code."""
    normalized_code = role_code.strip().lower()

    statement = select(Role).where(
        Role.code == normalized_code,
        Role.is_active.is_(True),
    )

    return db.scalar(statement)


def get_user_roles(
    db: Session,
    user_id: UUID,
) -> list[Role]:
    """Return active roles assigned to a user."""
    statement = (
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            Role.is_active.is_(True),
        )
        .order_by(Role.code)
    )

    return list(db.scalars(statement).all())


def get_user_role_codes(
    db: Session,
    user_id: UUID,
) -> set[str]:
    """Return active role codes assigned to a user."""
    roles = get_user_roles(
        db=db,
        user_id=user_id,
    )

    return {role.code for role in roles}


def user_has_role(
    db: Session,
    user_id: UUID,
    role_code: str,
) -> bool:
    """Return whether a user has the requested active role."""
    normalized_code = role_code.strip().lower()

    statement = (
        select(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user_id,
            Role.code == normalized_code,
            Role.is_active.is_(True),
        )
    )

    return db.scalar(statement) is not None


def assign_role(
    db: Session,
    user_id: UUID,
    role_code: str,
) -> UserRole:
    """Assign an active role to a user."""
    user = db.get(User, user_id)

    if user is None:
        raise ValueError("User not found.")

    role = get_role_by_code(
        db=db,
        role_code=role_code,
    )

    if role is None:
        raise ValueError("Active role not found.")

    existing_statement = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id,
    )

    existing_assignment = db.scalar(existing_statement)

    if existing_assignment is not None:
        return existing_assignment

    assignment = UserRole(
        user_id=user_id,
        role_id=role.id,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def remove_role(
    db: Session,
    user_id: UUID,
    role_code: str,
) -> bool:
    """Remove a role assignment from a user."""
    normalized_code = role_code.strip().lower()

    statement = (
        select(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user_id,
            Role.code == normalized_code,
        )
    )

    assignment = db.scalar(statement)

    if assignment is None:
        return False

    db.delete(assignment)
    db.commit()

    return True