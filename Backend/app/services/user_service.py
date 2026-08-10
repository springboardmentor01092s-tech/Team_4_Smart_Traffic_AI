"""
app/services/user_service.py

Business logic for user management (profile viewing and editing).

UserService is intentionally thin because most user operations are
simple CRUD with minimal business rules at this stage.
As the system grows, password policies, email change flows, and
admin operations can be added here without touching routers.
"""
from app.core.exceptions import UserNotFoundError
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate

logger = get_logger(__name__)


class UserService:
    """Service for user profile management operations."""

    def __init__(self, user_repo: UserRepository) -> None:
        self._repo = user_repo

    async def get_profile(self, user: User) -> User:
        """
        Return the authenticated user's profile.

        Currently a pass-through, but allows business logic to be inserted
        (e.g. activity tracking, audit logging) without changing the router.

        Args:
            user: The already-authenticated User instance from Depends.

        Returns:
            The User ORM instance (to be serialized by the router).
        """
        logger.debug("Profile fetched | id=%s", user.id)
        return user

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        """
        Update the authenticated user's mutable profile fields.

        Only non-None fields in `data` are written to the database.
        Password is hashed before storage if provided.

        Args:
            user: The authenticated User instance.
            data: Validated update payload (all fields optional).

        Returns:
            The updated User ORM instance.
        """
        update_fields: dict[str, object] = {}

        if data.full_name is not None:
            update_fields["full_name"] = data.full_name

        if data.password is not None:
            update_fields["hashed_password"] = hash_password(data.password)
            logger.info("Password changed | id=%s", user.id)

        if not update_fields:
            logger.debug("No update fields provided | id=%s", user.id)
            return user

        updated_user = await self._repo.update(user, **update_fields)
        logger.info("Profile updated | id=%s | fields=%s", user.id, list(update_fields.keys()))
        return updated_user
