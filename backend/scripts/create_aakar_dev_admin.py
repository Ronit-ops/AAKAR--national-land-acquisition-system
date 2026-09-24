import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from getpass import getpass

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import create_user


ROLE_CODE = "aakar_development_admin"
ROLE_NAME = "AAKAR Development Administrator"
ROLE_DESCRIPTION = (
    "Development-only operational role with all currently active "
    "AAKAR permissions. Do not use in production."
)

USER_EMAIL = "aakar.dev@example.com"
USER_NAME = "AAKAR Development Administrator"

REFERENCE_ROLE_CODE = "national_administrator"


def main() -> None:
    password = getpass(
        "Enter password for aakar.dev@example.com: "
    )

    if len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # 1. Get a valid operational scope level
        # ---------------------------------------------------------
        reference_role = db.scalar(
            select(Role).where(
                Role.code == REFERENCE_ROLE_CODE,
                Role.is_active.is_(True),
            )
        )

        if reference_role is None:
            raise RuntimeError(
                "The reference role "
                f"'{REFERENCE_ROLE_CODE}' does not exist "
                "as an active role."
            )

        # ---------------------------------------------------------
        # 2. Create or reuse development role
        # ---------------------------------------------------------
        role = db.scalar(
            select(Role).where(
                Role.code == ROLE_CODE,
            )
        )

        if role is None:
            role = Role(
                code=ROLE_CODE,
                name=ROLE_NAME,
                scope_level=reference_role.scope_level,
                description=ROLE_DESCRIPTION,
                is_system_role=False,
                is_active=True,
            )

            db.add(role)
            db.commit()
            db.refresh(role)

            print(
                f"Created role: {ROLE_CODE}"
            )

        else:
            role.name = ROLE_NAME
            role.scope_level = (
                reference_role.scope_level
            )
            role.description = ROLE_DESCRIPTION
            role.is_system_role = False
            role.is_active = True

            db.commit()
            db.refresh(role)

            print(
                f"Role already exists: {ROLE_CODE}"
            )

        # ---------------------------------------------------------
        # 3. Get all active permissions
        # ---------------------------------------------------------
        permissions = list(
            db.scalars(
                select(Permission)
                .where(
                    Permission.is_active.is_(True),
                )
                .order_by(
                    Permission.code,
                )
            ).all()
        )

        if not permissions:
            raise RuntimeError(
                "No active permissions exist in the database."
            )

        # ---------------------------------------------------------
        # 4. Assign all active permissions to role
        # ---------------------------------------------------------
        new_permission_assignments = 0

        for permission in permissions:
            existing_assignment = db.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id
                    == permission.id,
                )
            )

            if existing_assignment is None:
                db.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )

                new_permission_assignments += 1

        db.commit()

        print(
            f"Active permissions found: {len(permissions)}"
        )

        print(
            "New role-permission assignments: "
            f"{new_permission_assignments}"
        )

        # ---------------------------------------------------------
        # 5. Create or reuse development user
        # ---------------------------------------------------------
        user = db.scalar(
            select(User).where(
                User.email == USER_EMAIL,
            )
        )

        if user is None:
            user = create_user(
                db=db,
                email=USER_EMAIL,
                password=password,
                full_name=USER_NAME,
                commit=True,
            )

            print(
                f"Created user: {USER_EMAIL}"
            )

        else:
            user.is_active = True

            db.commit()
            db.refresh(user)

            print(
                f"User already exists: {USER_EMAIL}"
            )

        # ---------------------------------------------------------
        # 6. Assign development role to user
        # ---------------------------------------------------------
        existing_user_role = db.scalar(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id,
            )
        )

        if existing_user_role is None:
            db.add(
                UserRole(
                    user_id=user.id,
                    role_id=role.id,
                )
            )

            db.commit()

            print(
                f"Assigned role '{ROLE_CODE}' "
                f"to {USER_EMAIL}"
            )

        else:
            print(
                f"Role '{ROLE_CODE}' is already assigned "
                f"to {USER_EMAIL}"
            )

        # ---------------------------------------------------------
        # 7. Verify permission count
        # ---------------------------------------------------------
        verified_permission_count = db.scalar(
            select(
                func.count(Permission.id)
            )
            .join(
                RolePermission,
                RolePermission.permission_id
                == Permission.id,
            )
            .where(
                RolePermission.role_id == role.id,
                Permission.is_active.is_(True),
            )
        ) or 0

        print()
        print("=" * 60)
        print("AAKAR DEVELOPMENT ADMIN READY")
        print("=" * 60)
        print(
            f"Email             : {USER_EMAIL}"
        )
        print(
            f"Role              : {ROLE_CODE}"
        )
        print(
            f"Scope level       : {role.scope_level}"
        )
        print(
            f"Active permissions: {verified_permission_count}"
        )
        print("=" * 60)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()