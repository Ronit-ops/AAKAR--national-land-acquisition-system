from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.authority import Authority
from app.models.department import Department
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


def set_user_organization(
    db: Session,
    user_id: UUID,
    *,
    department_id: UUID | None,
    authority_id: UUID | None,
    commit: bool = True,
) -> User:
    """Assign or clear a user's department and authority."""
    user = get_user(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise ValueError("User not found.")

    if authority_id is not None and department_id is None:
        raise ValueError("An authority requires a department.")

    department = None

    if department_id is not None:
        department = db.get(Department, department_id)

        if department is None:
            raise ValueError("Department not found.")

        if not department.is_active:
            raise ValueError(
                "Cannot assign a user to an inactive department."
            )

    authority = None

    if authority_id is not None:
        authority = db.get(Authority, authority_id)

        if authority is None:
            raise ValueError("Authority not found.")

        if not authority.is_active:
            raise ValueError(
                "Cannot assign a user to an inactive authority."
            )

        if authority.department_id != department_id:
            raise ValueError(
                "Authority does not belong to the selected department."
            )

    user.department_id = department_id
    user.authority_id = authority_id

    if commit:
        db.commit()
        db.refresh(user)
    else:
        db.flush()

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
