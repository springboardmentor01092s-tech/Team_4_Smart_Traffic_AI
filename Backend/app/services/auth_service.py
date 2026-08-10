"""
app/services/auth_service.py

Business logic for authentication operations.

AuthService coordinates between:
  - UserRepository (data access)
  - security module (password hashing + JWT)
  - Domain exceptions (raised for callers to catch)

This service is HTTP-agnostic — it knows nothing about FastAPI, requests,
or responses. It operates purely on domain types and raises domain exceptions.
"""
from app.core.config import settings
from app.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserInactiveError,
)
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse

logger = get_logger(__name__)


class AuthService:
    """
    Service for authentication operations.

    Instantiated per-request with an injected repository.
    All methods are async.
    """

    def __init__(self, user_repo: UserRepository) -> None:
        self._repo = user_repo

    async def register(self, data: RegisterRequest) -> User:
        """
        Register a new user account.

        Steps:
            1. Check email uniqueness.
            2. Hash the plain-text password.
            3. Persist the new user via repository.

        Args:
            data: Validated registration request schema.

        Returns:
            The newly created User ORM instance.

        Raises:
            UserAlreadyExistsError: If email is already registered.
        """
        if await self._repo.exists_by_email(data.email):
            logger.warning("Registration rejected: duplicate email | email=%s", data.email)
            raise UserAlreadyExistsError(data.email)

        hashed = hash_password(data.password)
        user = await self._repo.create(
            full_name=data.full_name,
            email=data.email,
            hashed_password=hashed,
            role=UserRole.PUBLIC_USER,  # All self-registrations default to PUBLIC_USER
        )
        logger.info("User registered successfully | id=%s | email=%s", user.id, user.email)
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate a user and return a JWT access token.

        Steps:
            1. Look up user by email.
            2. Verify bcrypt hash.
            3. Check account is active.
            4. Mint and return a signed JWT.

        Args:
            email: The email address from the login request.
            password: The plain-text password from the login request.

        Returns:
            A TokenResponse containing the JWT and expiry info.

        Raises:
            InvalidCredentialsError: If email not found or password wrong.
            UserInactiveError: If the account has been deactivated.
        """
        user = await self._repo.get_by_email(email)

        # Use a constant-time comparison path regardless of whether user exists
        # to prevent email enumeration via timing attacks.
        if user is None or not verify_password(password, user.hashed_password):
            logger.warning("Login failed: invalid credentials | email=%s", email)
            raise InvalidCredentialsError()

        if not user.is_active:
            logger.warning("Login rejected: inactive account | id=%s", user.id)
            raise UserInactiveError()

        token = create_access_token(
            subject=str(user.id),
            additional_claims={"role": user.role, "email": user.email},
        )

        logger.info("User logged in | id=%s | email=%s | role=%s", user.id, user.email, user.role)
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
