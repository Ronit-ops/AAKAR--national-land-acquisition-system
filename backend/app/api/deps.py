from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.jwt import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id
from app.services.rbac_service import get_user_role_codes


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated active user."""
    authentication_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise authentication_error

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise authentication_error from None

    subject = payload.get("sub")

    if not isinstance(subject, str):
        raise authentication_error

    try:
        user_id = UUID(subject)
    except ValueError:
        raise authentication_error from None

    user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if user is None or not user.is_active:
        raise authentication_error

    return user


def require_role(
    role_code: str,
) -> Callable:
    """
    Create a dependency that requires one specific active role.

    Authentication is checked first. Authorization is checked against
    the user's current active roles stored in the database.
    """
    normalized_role_code = role_code.strip().lower()

    if not normalized_role_code:
        raise ValueError("role_code must not be empty.")

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


def require_any_role(
    *role_codes: str,
) -> Callable:
    """
    Create a dependency that requires at least one active role.
    """
    normalized_role_codes = {
        role_code.strip().lower()
        for role_code in role_codes
        if role_code.strip()
    }

    if not normalized_role_codes:
        raise ValueError("At least one role_code must be provided.")

    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Session = Depends(get_db),
    ) -> User:
        current_role_codes = get_user_role_codes(
            db=db,
            user_id=current_user.id,
        )

        if current_role_codes.isdisjoint(normalized_role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_dependency