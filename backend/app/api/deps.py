from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.jwt import decode_access_token
from app.db.session import get_db
from app.services.auth_service import get_user_by_id
from app.services.rbac_service import (
    get_user_permission_codes,
    get_user_role_codes,
)
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated active user from the bearer token."""
    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
    )

    if credentials is None:
        raise authentication_error

    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")

        if not subject:
            raise authentication_error

        user_id = UUID(subject)
    except (ValueError, TypeError, jwt.PyJWTError):
        raise authentication_error from None

    user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if user is None or not user.is_active:
        raise authentication_error

    return user


def require_role(role_code: str) -> Callable:
    """Require the authenticated user to have one active role."""
    normalized_role_code = role_code.strip().lower()

    if not normalized_role_code:
        raise ValueError("Role code must not be empty.")

    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
    ) -> User:
        role_codes = get_user_role_codes(
            db=db,
            user_id=current_user.id,
        )

        if normalized_role_code not in role_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_dependency


def require_any_role(*role_codes: str) -> Callable:
    """Require the authenticated user to have at least one active role."""
    normalized_role_codes = {
        role_code.strip().lower()
        for role_code in role_codes
        if role_code.strip()
    }

    if not normalized_role_codes:
        raise ValueError("At least one role code must be provided.")

    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
    ) -> User:
        user_role_codes = get_user_role_codes(
            db=db,
            user_id=current_user.id,
        )

        if not normalized_role_codes.intersection(user_role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_dependency


def require_permission(permission_code: str) -> Callable:
    """Require the authenticated user to have one active permission."""
    normalized_permission_code = permission_code.strip().lower()

    if not normalized_permission_code:
        raise ValueError("Permission code must not be empty.")

    def permission_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
    ) -> User:
        permission_codes = get_user_permission_codes(
            db=db,
            user_id=current_user.id,
        )

        if normalized_permission_code not in permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return permission_dependency


def require_any_permission(*permission_codes: str) -> Callable:
    """Require the authenticated user to have at least one active permission."""
    normalized_permission_codes = {
        permission_code.strip().lower()
        for permission_code in permission_codes
        if permission_code.strip()
    }

    if not normalized_permission_codes:
        raise ValueError("At least one permission code must be provided.")

    def permission_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
    ) -> User:
        user_permission_codes = get_user_permission_codes(
            db=db,
            user_id=current_user.id,
        )

        if not normalized_permission_codes.intersection(
            user_permission_codes,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return permission_dependency