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

---

## Traffic Cameras

> API endpoints for managing IoT traffic camera units.

### `GET /api/v1/cameras`

List traffic cameras with optional filtering. Accessible by any authenticated user.

**Headers**
```
Authorization: Bearer <access_token>
```

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by `ACTIVE`, `OFFLINE`, or `MAINTENANCE` |
| `skip` | int | Pagination offset (default: 0) |
| `limit` | int | Pagination limit (default: 100, max: 500) |

**Response 200 — OK**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "I-95 North Mile 42",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "status": "ACTIVE",
    "created_at": "2025-01-15T10:30:00+00:00",
    "updated_at": "2025-01-15T10:30:00+00:00"
  }
]
```

---

### `POST /api/v1/cameras`

Register a new traffic camera. Requires `ADMIN` role.

**Headers**
```
Authorization: Bearer <access_token>
```

**Request Body**
```json
{
  "name": "I-95 North Mile 42",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "status": "ACTIVE"
}
```

**Response 201 — Created**
Returns the created camera object.

---

### `GET /api/v1/cameras/{camera_id}`

Get a specific camera by ID. Accessible by any authenticated user.

**Response 200 — OK**
Returns the camera object.

**Error Responses**
- `404 Not Found`: Camera does not exist or was soft-deleted.

---

### `PUT /api/v1/cameras/{camera_id}`

Update a specific camera. Requires `ADMIN` role. All fields are optional.

**Request Body**
```json
{
  "status": "MAINTENANCE"
}
```

**Response 200 — OK**
Returns the updated camera object.

---

### `DELETE /api/v1/cameras/{camera_id}`

Soft-delete a specific camera. Requires `ADMIN` role.

**Response 204 — No Content**
Successfully deleted.

**Error Responses**
- `400 Bad Request`: Camera cannot be deleted because it is still linked to active Traffic Segments.

---

## Traffic Segments

> API endpoints for managing logical road segments spanning between cameras.

### `GET /api/v1/segments`

List traffic segments. Accessible by any authenticated user.

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by `ACTIVE`, `CONSTRUCTION`, or `CLOSED` |
| `camera_id` | UUID | Filter segments linked to a specific camera |
| `skip` | int | Pagination offset (default: 0) |
| `limit` | int | Pagination limit (default: 100) |

**Response 200 — OK**
```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "camera_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "I-95 Northbound Segment 42-43",
    "start_latitude": 40.7128,
    "start_longitude": -74.0060,
    "end_latitude": 40.7150,
    "end_longitude": -74.0080,
    "status": "ACTIVE",
    "created_at": "2025-01-15T10:30:00+00:00",
    "updated_at": "2025-01-15T10:30:00+00:00"
  }
]
```

---

### `POST /api/v1/segments`

Create a new traffic segment. Requires `ADMIN` role.

**Request Body**
Must contain all fields shown in the segment response above, excluding `id`, `created_at`, and `updated_at`.

**Response 201 — Created**
Returns the created segment.

---

### `GET /api/v1/segments/{segment_id}`

Get a specific segment. Accessible by any authenticated user.

---

### `PUT /api/v1/segments/{segment_id}`

Update a segment. Requires `ADMIN` role.

---

### `DELETE /api/v1/segments/{segment_id}`

Soft-delete a segment. Requires `ADMIN` role.

---

### `GET /api/v1/segments/{segment_id}/latest-reading`

Retrieve the most recent traffic reading for a specific segment. Accessible by any authenticated user.

**Response 200 — OK**
```json
{
  "id": 1,
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "vehicle_count": 45,
  "avg_speed_kmh": 65.5,
  "congestion_level": "MODERATE",
  "confidence_score": 95.0,
  "recorded_at": "2025-01-15T10:35:00+00:00",
  "created_at": "2025-01-15T10:35:05+00:00"
}
```
*(Returns `null` if no readings exist).*

---

## Traffic Readings

> API endpoints for high-throughput time-series traffic data.

### `GET /api/v1/readings`

List historical traffic readings. Accessible by any authenticated user.

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `segment_id` | UUID | Filter readings for a specific segment |
| `from_dt` | datetime | Return readings recorded after this time |
| `to_dt` | datetime | Return readings recorded before this time |
| `congestion_level` | string | Filter by congestion level |

**Response 200 — OK**
Returns a list of reading objects.

---

### `POST /api/v1/readings`

Submit a new traffic reading. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Request Body**
```json
{
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "vehicle_count": 45,
  "avg_speed_kmh": 65.5,
  "congestion_level": "MODERATE",
  "confidence_score": 95.0,
  "recorded_at": "2025-01-15T10:35:00+00:00"
}
```

**Response 201 — Created**
Returns the persisted reading object.

**Error Responses**
- `422 Unprocessable Entity`: Raised if `recorded_at` is a future date.
- `404 Not Found`: Raised if `segment_id` does not refer to a valid, active segment.

---

### `GET /api/v1/readings/{reading_id}`

Get a specific traffic reading by its BIGSERIAL ID. Accessible by any authenticated user.

**Response 200 — OK**
Returns the specific reading object.

---

## Traffic Alerts

> API endpoints for managing traffic alerts and incidents on segments.

### `GET /api/v1/alerts`

List traffic alerts. Accessible by any authenticated user.

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `segment_id` | UUID | Filter alerts for a specific segment |
| `status` | string | Filter by `ACTIVE`, `RESOLVED`, or `DISMISSED` |
| `severity` | string | Filter by `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` |
| `alert_type` | string | Filter by alert category (`CONGESTION`, `ACCIDENT`, etc) |
| `skip` | int | Pagination offset (default: 0) |
| `limit` | int | Pagination limit (default: 100) |

**Response 200 — OK**
Returns a list of alert objects.

---

### `POST /api/v1/alerts`

Create a new traffic alert. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Request Body**
```json
{
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "title": "Severe Congestion",
  "description": "Traffic is completely stopped.",
  "alert_type": "CONGESTION",
  "severity": "CRITICAL"
}
```

**Response 201 — Created**
Returns the created alert object.

---

### `GET /api/v1/alerts/{alert_id}`

Get a specific traffic alert. Accessible by any authenticated user.

**Response 200 — OK**
Returns the specific alert object.

---

### `PUT /api/v1/alerts/{alert_id}`

Update a traffic alert. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role. 
Only fields like `title`, `description`, and `severity` can be updated.

**Response 200 — OK**
Returns the updated alert.
**Error Responses**
- `409 Conflict`: Raised if the alert is not in `ACTIVE` state.

---

### `PATCH /api/v1/alerts/{alert_id}/resolve`

Resolve a traffic alert. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.
Transitions status to `RESOLVED` and sets `resolved_at`.

**Response 200 — OK**
Returns the updated alert.

---

### `PATCH /api/v1/alerts/{alert_id}/dismiss`

Dismiss a traffic alert. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.
Transitions status to `DISMISSED` and sets `resolved_at`.

**Response 200 — OK**
Returns the updated alert.

---

### `DELETE /api/v1/alerts/{alert_id}`

Soft-delete an alert. Requires `ADMIN` role.

**Response 204 — No Content**
Successfully deleted.

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
