"""
app/repositories/user_repository.py

Data access layer for the User entity.

Responsibilities:
  - All async SQLAlchemy queries for User records.
  - No business logic. No HTTP concerns. No password hashing.
  - Accepts an AsyncSession injected by the caller (Depends(get_db)).

Why a repository?
  - Services remain testable without a real database.
  - DB query changes are localized here — services don't change.
  - Easy to swap for a different DB driver in the future.
"""
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.user import User, UserRole

logger = get_logger(__name__)


class UserRepository:
    """
    Repository for User persistence operations.

    Instantiated per-request with an injected AsyncSession.
    All methods are async to avoid blocking the event loop.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ─── Read ────────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return a User by primary key, or None if not found."""
        result = await self._db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Return a User by email address (case-sensitive), or None."""
        result = await self._db.execute(
            select(User).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_all(self, *, skip: int = 0, limit: int = 100) -> Sequence[User]:
        """Return a paginated list of all users. Reserved for Admin use."""
        result = await self._db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user with the given email already exists."""
        result = await self._db.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None

    # ─── Write ───────────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        full_name: str,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.PUBLIC_USER,
    ) -> User:
        """
        Persist a new User and return the created instance.

        The session commit is handled by the get_db dependency.
        After this method returns, the object is in 'pending' state
        until the session commits.
        """
        user = User(
            full_name=full_name.strip(),
            email=email.lower().strip(),
            hashed_password=hashed_password,
            role=role,
        )
        self._db.add(user)
        await self._db.flush()  # Assign DB-generated fields (id, timestamps)
        await self._db.refresh(user)  # Reload from DB to get all defaults
        logger.info("User created | id=%s | email=%s | role=%s", user.id, user.email, user.role)
        return user

    async def update(self, user: User, **fields: object) -> User:
        """
        Update arbitrary fields on a User instance.

        Args:
            user: The ORM instance to update.
            **fields: Keyword arguments mapping column names to new values.

        Returns:
            The updated User instance (refreshed from DB).
        """
        for field, value in fields.items():
            if hasattr(user, field) and value is not None:
                setattr(user, field, value)
        self._db.add(user)
        await self._db.flush()
        await self._db.refresh(user)
        logger.info("User updated | id=%s | fields=%s", user.id, list(fields.keys()))
        return user

    async def delete(self, user: User) -> None:
        """
        Hard-delete a user record from the database.

        Prefer is_active=False (soft delete) for production use cases.
        """
        await self._db.delete(user)
        await self._db.flush()
        logger.warning("User hard-deleted | id=%s | email=%s", user.id, user.email)
