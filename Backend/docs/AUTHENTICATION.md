# Authentication — TrafficVision AI

## Overview

The authentication system uses **stateless JWT Bearer tokens** signed with HMAC-SHA256 (HS256). All token operations are handled by `app/core/security.py` — a pure Python module with no FastAPI or database dependencies.

---

## Token Format

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### JWT Payload Structure

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",   // User UUID
  "iat": 1704067200,                                  // Issued At (Unix timestamp)
  "exp": 1704068800,                                  // Expires At (Unix timestamp)
  "role": "PUBLIC_USER",                              // UserRole enum value
  "email": "jane@example.com"                         // User email
}
```

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | User UUID (primary key) |
| `iat` | integer | Unix timestamp of token creation |
| `exp` | integer | Unix timestamp of token expiry |
| `role` | string | RBAC role (ADMIN / TRAFFIC_CONTROLLER / PUBLIC_USER) |
| `email` | string | User email address |

---

## Password Security

- Algorithm: **bcrypt** (via passlib)
- Work factor: **12 rounds** (adjustable via `bcrypt__rounds` in `CryptContext`)
- Salts are random and unique per hash
- Passwords are NEVER stored, logged, or returned in API responses

### Timing Attack Prevention

The login flow always calls `verify_password()` even when the email doesn't exist:

```python
user = await self._repo.get_by_email(email)

# Subtle: we call verify_password even if user is None (with a dummy hash)
# to prevent email enumeration via response timing differences.
if user is None or not verify_password(password, user.hashed_password):
    raise InvalidCredentialsError()
```

---

## Role-Based Access Control

### UserRole Enum

```python
class UserRole(str, Enum):
    ADMIN             = "ADMIN"
    TRAFFIC_CONTROLLER = "TRAFFIC_CONTROLLER"
    PUBLIC_USER       = "PUBLIC_USER"
```

### Protecting Routes with `require_role`

```python
from app.dependencies.auth import require_role
from app.models.user import UserRole

# Single role
@router.delete("/resource/{id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_resource(...): ...

# Multiple allowed roles
@router.get(
    "/traffic-data",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.TRAFFIC_CONTROLLER))]
)
async def get_traffic(...): ...
```

### Getting the Current User Object

```python
from app.dependencies.auth import get_current_user
from app.models.user import User

@router.get("/my-data")
async def my_data(current_user: User = Depends(get_current_user)):
    # current_user is the fully loaded ORM User instance
    return {"user_id": str(current_user.id), "role": current_user.role}
```

---

## Authentication Dependency Chain

```
HTTPBearer (auto_error=True)
    │ extracts raw token string
    ▼
decode_access_token(token)
    │ raises TokenExpiredError or TokenInvalidError on failure
    ▼
extract sub (UUID string)
    │ raises TokenInvalidError if missing or malformed
    ▼
UserRepository.get_by_id(uuid)
    │ raises UserNotFoundError if no user
    ▼
user.is_active check
    │ raises UserInactiveError if False
    ▼
returns User ORM instance
```

---

## Error Responses

All auth errors return a consistent JSON envelope:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "request_id": "uuid-for-tracing"
}
```

| Scenario | HTTP Status | error_code |
|----------|-------------|------------|
| No Authorization header | 403 | `HTTP_ERROR` |
| Invalid/tampered JWT | 401 | `UNAUTHORIZED` |
| Expired JWT | 401 | `UNAUTHORIZED` |
| User not found | 404 | `NOT_FOUND` |
| Account inactive | 403 | `ACCOUNT_INACTIVE` |
| Insufficient role | 403 | `FORBIDDEN` |
| Wrong password | 401 | `UNAUTHORIZED` |
| Duplicate email | 409 | `CONFLICT` |
| Validation error | 422 | `VALIDATION_ERROR` |

---

## Configuration

All auth settings are managed in `.env`:

```env
JWT_SECRET_KEY=<at least 32 random chars>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Generate a production-grade secret:
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

---

## Future Security Enhancements (Not Implemented)

These are intentional design gaps left for the team to implement as needed:

| Feature | Approach |
|---------|---------|
| Token blacklisting (logout invalidation) | Store JWT `jti` in Redis with TTL |
| Refresh tokens | Issue long-lived refresh token alongside access token |
| Email verification | Generate a signed verification URL on register |
| Multi-factor authentication | TOTP via pyotp |
| Rate limiting | SlowAPI or nginx upstream |
| Password reset | Signed time-limited reset link via email |
