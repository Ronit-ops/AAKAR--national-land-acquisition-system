from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


def list_users(
    db: Session,
    *,
    search: str | None = None,
    is_active: bool | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[User], int]:
    """Return a filtered, paginated user list and total count."""
    normalized_search = search.strip().lower() if search else None

    conditions = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        conditions.append(
            or_(
                func.lower(User.email).like(search_pattern),
                func.lower(User.full_name).like(search_pattern),
            )
        )

    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))

    count_statement = select(func.count()).select_from(User)

    if conditions:
        count_statement = count_statement.where(*conditions)

    total = db.scalar(count_statement) or 0

    users_statement = (
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc(), User.id)
        .offset(offset)
        .limit(limit)
    )

    users = list(db.scalars(users_statement).all())

    return users, total


def get_user(
    db: Session,
    user_id: UUID,
) -> User | None:
    """Return a user by UUID."""
    statement = select(User).where(User.id == user_id)

    return db.scalar(statement)


def update_user_profile(
    db: Session,
    user_id: UUID,
    *,
    full_name: str,
    email: str,
    commit: bool = True,
) -> User:
    """Update a user's basic profile information."""
    user = get_user(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise ValueError("User not found.")

    normalized_name = full_name.strip()
    normalized_email = email.strip().lower()

    if not normalized_name:
        raise ValueError("Full name must not be empty.")

    if not normalized_email:
        raise ValueError("Email must not be empty.")

    existing_user = db.scalar(
        select(User).where(
            User.email == normalized_email,
            User.id != user_id,
        )
    )

    if existing_user is not None:
        raise ValueError("A user with this email already exists.")

    user.full_name = normalized_name
    user.email = normalized_email

    try:
        if commit:
            db.commit()
            db.refresh(user)
        else:
            db.flush()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A user with this email already exists."
        ) from None

    return user


def set_user_active_status(
    db: Session,
    user_id: UUID,
    *,
    is_active: bool,
    commit: bool = True,
) -> User:
    """Activate or deactivate a user account."""
    user = get_user(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise ValueError("User not found.")

    user.is_active = is_active

    if commit:
        db.commit()
        db.refresh(user)
    else:
        db.flush()

    return user