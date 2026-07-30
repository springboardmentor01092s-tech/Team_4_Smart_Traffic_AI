# API Reference — TrafficVision AI

**Base URL:** `http://localhost:8000`
**API Version Prefix:** `/api/v1`
**Authentication:** Bearer JWT token in `Authorization` header

---

## Health Check

### `GET /api/v1/health`

Returns the service health status. No authentication required.

**Response 200**
```json
{
  "status": "healthy",
  "service": "TrafficVision AI",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2025-01-15T10:30:00+00:00"
}
```

---

## Authentication

### `POST /api/v1/auth/register`

Register a new user account.

**Request Body**
```json
{
  "full_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "password": "Str0ng1Pass"
}
```

| Field | Type | Rules |
|-------|------|-------|
| `full_name` | string | 2–255 characters, required |
| `email` | string | Valid email format, unique, required |
| `password` | string | 8–128 chars, must contain letter + digit |

**Response 201 — Created**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "PUBLIC_USER",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

**Error Responses**

| Status | error_code | Cause |
|--------|-----------|-------|
| 409 | `CONFLICT` | Email already registered |
| 422 | `VALIDATION_ERROR` | Invalid/missing fields |

---

### `POST /api/v1/auth/login`

Authenticate and receive a JWT access token.

**Request Body**
```json
{
  "email": "jane.doe@example.com",
  "password": "Str0ng1Pass"
}
```

**Response 200 — OK**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

| Field | Description |
|-------|-------------|
| `access_token` | Signed JWT string |
| `token_type` | Always `"bearer"` |
| `expires_in` | Seconds until expiry (default: 1800) |

**Using the token in subsequent requests:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Error Responses**

| Status | error_code | Cause |
|--------|-----------|-------|
| 401 | `UNAUTHORIZED` | Wrong email or password |
| 403 | `ACCOUNT_INACTIVE` | Account has been deactivated |
| 422 | `VALIDATION_ERROR` | Invalid request format |

---

### `POST /api/v1/auth/logout`

Acknowledge a logout request. The client must discard the token.

> JWTs are stateless — the server cannot invalidate a token without a blacklist (Redis). The client is responsible for deleting the stored token.

**No request body required.**

**Response 200 — OK**
```json
{
  "message": "Successfully logged out."
}
```

---

## User Management

> All endpoints in this section require a valid Bearer JWT.

### `GET /api/v1/users/me`

Return the authenticated user's profile.

**Headers**
```
Authorization: Bearer <access_token>
```

**Response 200 — OK**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Jane Doe",
  "email": "jane.doe@example.com",
  "role": "PUBLIC_USER",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

**Error Responses**

| Status | error_code | Cause |
|--------|-----------|-------|
| 403 | `HTTP_ERROR` | Missing Authorization header |
| 401 | `UNAUTHORIZED` | Invalid or expired token |

---

### `PUT /api/v1/users/me`

Update the authenticated user's mutable profile fields.

All fields are optional. Only provided fields are updated.

**Headers**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body (all fields optional)**
```json
{
  "full_name": "Jane Smith",
  "password": "NewStr0ng1Pass"
}
```

| Field | Type | Rules |
|-------|------|-------|
| `full_name` | string \| null | 2–255 characters |
| `password` | string \| null | 8–128 chars, letter + digit |

**Response 200 — OK** — Returns the updated profile (same shape as `GET /users/me`)

**Error Responses**

| Status | error_code | Cause |
|--------|-----------|-------|
| 401 | `UNAUTHORIZED` | Invalid/expired token |
| 422 | `VALIDATION_ERROR` | Field validation failure |

---

## Standard Error Envelope

All error responses use this consistent JSON structure:

```json
{
  "detail": "Human-readable description of what went wrong",
  "error_code": "MACHINE_READABLE_ERROR_CODE",
  "request_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
}
```

Validation errors (422) include an `errors` array:

```json
{
  "detail": "Request validation failed.",
  "error_code": "VALIDATION_ERROR",
  "request_id": "...",
  "errors": [
    {
      "field": "body -> password",
      "message": "Password must contain at least one letter and one digit.",
      "type": "value_error"
    }
  ]
}
```

---

## Interactive Documentation

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

Click the **Authorize 🔒** button in Swagger UI and paste your Bearer token to test protected endpoints.
