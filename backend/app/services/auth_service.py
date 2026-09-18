from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    """Return a user by normalized email address."""
    normalized_email = email.strip().lower()

    statement = select(User).where(User.email == normalized_email)

    return db.scalar(statement)


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str,
) -> User:
    """Create a new user with a securely hashed password."""
    normalized_email = email.strip().lower()

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user and record the successful login time."""
    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    user.last_login_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(user)

    return user


def get_user_by_id(
    db: Session,
    user_id: UUID,
) -> User | None:
    """Return a user by UUID."""
    statement = select(User).where(User.id == user_id)

    return db.scalar(statement)