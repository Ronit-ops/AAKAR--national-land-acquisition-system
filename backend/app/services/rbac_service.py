from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
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


def get_permission_by_code(
    db: Session,
    permission_code: str,
) -> Permission | None:
    """Return an active permission by its normalized machine-readable code."""
    normalized_code = permission_code.strip().lower()

    statement = select(Permission).where(
        Permission.code == normalized_code,
        Permission.is_active.is_(True),
    )

    return db.scalar(statement)


def get_user_permissions(
    db: Session,
    user_id: UUID,
) -> list[Permission]:
    """Return distinct active permissions granted through active user roles."""
    statement = (
        select(Permission)
        .join(
            RolePermission,
            RolePermission.permission_id == Permission.id,
        )
        .join(
            Role,
            Role.id == RolePermission.role_id,
        )
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .where(
            UserRole.user_id == user_id,
            Role.is_active.is_(True),
            Permission.is_active.is_(True),
        )
        .distinct()
        .order_by(Permission.code)
    )

    return list(db.scalars(statement).all())


def get_user_permission_codes(
    db: Session,
    user_id: UUID,
) -> set[str]:
    """Return active permission codes granted to a user."""
    permissions = get_user_permissions(
        db=db,
        user_id=user_id,
    )

    return {permission.code for permission in permissions}


def user_has_permission(
    db: Session,
    user_id: UUID,
    permission_code: str,
) -> bool:
    """Return whether a user has the requested active permission."""
    normalized_code = permission_code.strip().lower()

    statement = (
        select(RolePermission)
        .join(
            Role,
            Role.id == RolePermission.role_id,
        )
        .join(
            UserRole,
            UserRole.role_id == Role.id,
        )
        .join(
            Permission,
            Permission.id == RolePermission.permission_id,
        )
        .where(
            UserRole.user_id == user_id,
            Role.is_active.is_(True),
            Permission.code == normalized_code,
            Permission.is_active.is_(True),
        )
    )

    return db.scalar(statement) is not None


def get_role_permissions(
    db: Session,
    role_code: str,
) -> list[RolePermission]:
    """Return permission assignments for an active role."""
    role = get_role_by_code(
        db=db,
        role_code=role_code,
    )

    if role is None:
        raise ValueError("Active role not found.")

    statement = (
        select(RolePermission)
        .join(
            Permission,
            Permission.id == RolePermission.permission_id,
        )
        .where(
            RolePermission.role_id == role.id,
        )
        .order_by(Permission.code)
    )

    return list(db.scalars(statement).all())


def assign_permission_to_role(
    db: Session,
    role_code: str,
    permission_code: str,
) -> RolePermission:
    """Assign an active permission to an active role."""
    role = get_role_by_code(
        db=db,
        role_code=role_code,
    )

    if role is None:
        raise ValueError("Active role not found.")

    permission = get_permission_by_code(
        db=db,
        permission_code=permission_code,
    )

    if permission is None:
        raise ValueError("Active permission not found.")

    existing_statement = select(RolePermission).where(
        RolePermission.role_id == role.id,
        RolePermission.permission_id == permission.id,
    )

    existing_assignment = db.scalar(existing_statement)

    if existing_assignment is not None:
        return existing_assignment

    assignment = RolePermission(
        role_id=role.id,
        permission_id=permission.id,
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def remove_permission_from_role(
    db: Session,
    role_code: str,
    permission_code: str,
) -> bool:
    """Remove a permission assignment from a role."""
    normalized_role_code = role_code.strip().lower()
    normalized_permission_code = permission_code.strip().lower()

    statement = (
        select(RolePermission)
        .join(
            Role,
            Role.id == RolePermission.role_id,
        )
        .join(
            Permission,
            Permission.id == RolePermission.permission_id,
        )
        .where(
            Role.code == normalized_role_code,
            Permission.code == normalized_permission_code,
        )
    )

    assignment = db.scalar(statement)

    if assignment is None:
        return False

    db.delete(assignment)
    db.commit()

    return True