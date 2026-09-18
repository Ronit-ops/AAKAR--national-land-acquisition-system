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


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Session = Depends(get_db),
) -> User:
    """Return the active user represented by the bearer token."""

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