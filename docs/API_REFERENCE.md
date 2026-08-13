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

**Response 200 — OK**
```json
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
```

**Error Responses**
- `404 Not Found`: Segment does not exist or was soft-deleted.

---

### `PUT /api/v1/segments/{segment_id}`

Update a segment. Requires `ADMIN` role.

**Request Body**
All fields are optional.
```json
{
  "status": "CONSTRUCTION"
}
```

**Response 200 — OK**
Returns the updated segment object.

**Error Responses**
- `404 Not Found`: Segment does not exist or was soft-deleted.

---

### `DELETE /api/v1/segments/{segment_id}`

Soft-delete a segment. Requires `ADMIN` role.

**Response 204 — No Content**
Successfully deleted.

**Error Responses**
- `404 Not Found`: Segment does not exist or was already soft-deleted.

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
```json
[
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
]
```

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

**Error Responses**
- `404 Not Found`: Reading does not exist.

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
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "segment_id": "660e8400-e29b-41d4-a716-446655440001",
    "title": "Severe Congestion",
    "description": "Traffic is completely stopped.",
    "alert_type": "CONGESTION",
    "severity": "CRITICAL",
    "status": "ACTIVE",
    "resolved_at": null,
    "created_at": "2025-01-15T10:30:00+00:00",
    "updated_at": "2025-01-15T10:30:00+00:00"
  }
]
```

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
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "title": "Severe Congestion",
  "description": "Traffic is completely stopped.",
  "alert_type": "CONGESTION",
  "severity": "CRITICAL",
  "status": "ACTIVE",
  "resolved_at": null,
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

**Error Responses**
- `404 Not Found`: Alert does not exist or was soft-deleted.

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

## Traffic Predictions

> API endpoints for managing AI-driven traffic predictions.

### `POST /api/v1/predictions/segment/{segment_id}/forecast`

Generate a traffic congestion forecast using the ML PredictionEngine. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Request Body**
```json
{
  "horizon_minutes": 60
}
```

**Response 201 — Created**
Returns the persisted prediction object with status `COMPLETED` (or `FAILED` if prediction encounters an error).
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "prediction_for": "2025-01-15T11:30:00+00:00",
  "horizon_minutes": 60,
  "model_version": "rf-v2-150-a1b2c3d4",
  "status": "COMPLETED",
  "predicted_congestion_level": "HEAVY",
  "predicted_vehicle_count": 120,
  "predicted_avg_speed_kmh": 35.5,
  "confidence_score": 0.85,
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

**Error Responses**
- `422 Unprocessable Entity`: Raised if there are insufficient historical readings (`INSUFFICIENT_READINGS`) to train the model, or invalid parameters.
- `404 Not Found`: Segment does not exist.

---

### `GET /api/v1/predictions`

List traffic predictions. Accessible by any authenticated user.

**Query Parameters**
| Parameter | Type | Description |
|-----------|------|-------------|
| `segment_id` | UUID | Filter predictions for a specific segment |
| `status` | string | Filter by `PENDING`, `COMPLETED`, or `FAILED` |
| `skip` | int | Pagination offset (default: 0) |
| `limit` | int | Pagination limit (default: 100) |

**Response 200 — OK**
```json
[
  {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "segment_id": "660e8400-e29b-41d4-a716-446655440001",
    "prediction_for": "2025-01-15T11:30:00+00:00",
    "horizon_minutes": 60,
    "model_version": "v1.2.0",
    "status": "PENDING",
    "predicted_congestion_level": null,
    "predicted_vehicle_count": null,
    "predicted_avg_speed_kmh": null,
    "confidence_score": null,
    "created_at": "2025-01-15T10:30:00+00:00",
    "updated_at": "2025-01-15T10:30:00+00:00"
  }
]
```

---

### `POST /api/v1/predictions`

Request a new traffic prediction. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Request Body**
```json
{
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "prediction_for": "2025-01-15T11:30:00+00:00",
  "horizon_minutes": 60,
  "model_version": "v1.2.0"
}
```

**Response 201 — Created**
Returns the created prediction object with status `PENDING`.

---

### `GET /api/v1/predictions/{prediction_id}`

Get a specific traffic prediction. Accessible by any authenticated user.

**Response 200 — OK**
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "prediction_for": "2025-01-15T11:30:00+00:00",
  "horizon_minutes": 60,
  "model_version": "v1.2.0",
  "status": "PENDING",
  "predicted_congestion_level": null,
  "predicted_vehicle_count": null,
  "predicted_avg_speed_kmh": null,
  "confidence_score": null,
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

**Error Responses**
- `404 Not Found`: Prediction does not exist or was soft-deleted.

---

### `GET /api/v1/predictions/segment/{segment_id}/upcoming`

Get upcoming PENDING or COMPLETED predictions for a segment. Accessible by any authenticated user.

**Response 200 — OK**
```json
[
  {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "segment_id": "660e8400-e29b-41d4-a716-446655440001",
    "prediction_for": "2025-01-15T11:30:00+00:00",
    "horizon_minutes": 60,
    "model_version": "v1.2.0",
    "status": "PENDING",
    "predicted_congestion_level": null,
    "predicted_vehicle_count": null,
    "predicted_avg_speed_kmh": null,
    "confidence_score": null,
    "created_at": "2025-01-15T10:30:00+00:00",
    "updated_at": "2025-01-15T10:30:00+00:00"
  }
]
```

---

### `PATCH /api/v1/predictions/{prediction_id}/complete`

Submit the result of a traffic prediction model. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Request Body**
```json
{
  "predicted_congestion_level": "HEAVY",
  "predicted_vehicle_count": 120,
  "predicted_avg_speed_kmh": 35.5,
  "confidence_score": 0.85
}
```

**Response 200 — OK**
Returns the updated prediction with status `COMPLETED`.

---

### `PATCH /api/v1/predictions/{prediction_id}/fail`

Mark a pending prediction as FAILED. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Response 200 — OK**
Returns the updated prediction with status `FAILED`.

---

### `DELETE /api/v1/predictions/{prediction_id}`

Soft-delete a prediction. Requires `ADMIN` role.

**Response 204 — No Content**
Successfully deleted.

**Error Responses**
- `404 Not Found`: Prediction does not exist or was already soft-deleted.

---


## Module 6: Routes

### `GET /api/v1/routes/compare`
Compare multiple routes and get a recommendation based on estimated travel time and congestion. Accessible by any authenticated user.

**Query Parameters**
- `route_ids` (string, required): Comma-separated list of route UUIDs to compare.

**Response 200 — OK**
```json
{
  "recommended_route_id": "770e8400-e29b-41d4-a716-446655440001",
  "routes": [
    {
      "route_id": "770e8400-e29b-41d4-a716-446655440001",
      "estimated_travel_minutes": 25.5,
      "worst_congestion_level": "MODERATE",
      "is_recommended": true
    }
  ]
}
```

**Error Responses**
- `422 Unprocessable Entity`: No viable route could be evaluated (`NO_VIABLE_ROUTE`).

---

### `GET /api/v1/routes/{route_id}/estimate`
Estimate traversal time for a route using current traffic readings or speed limits. Accessible by any authenticated user.

**Response 200 — OK**
```json
{
  "route_id": "770e8400-e29b-41d4-a716-446655440001",
  "estimated_travel_minutes": 25.5,
  "segment_count": 3,
  "segments_with_readings": 2,
  "worst_congestion_level": "MODERATE",
  "segment_estimates": [
    {
      "segment_id": "660e8400-e29b-41d4-a716-446655440001",
      "estimated_minutes": 10.5,
      "speed_used_kmh": 45.2,
      "data_source": "reading"
    }
  ]
}
```

**Error Responses**
- `404 Not Found`: Route does not exist or was soft-deleted.

---

### `GET /api/v1/routes`
List all routes (paginated, non-deleted). Accessible by any authenticated user.

**Query Parameters**
- `is_active` (boolean, optional): Filter by active status
- `skip` (integer, default: 0)
- `limit` (integer, default: 100)

**Response 200 — OK**
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440001",
    "name": "Downtown Commute",
    "origin_name": "North Suburbs",
    "destination_name": "City Center",
    "total_distance_km": 15.5,
    "is_active": true,
    "created_at": "2025-01-15T10:30:00+00:00",
    "updated_at": "2025-01-15T10:30:00+00:00"
  }
]
```

---

### `GET /api/v1/routes/{route_id}`
Get detailed route information including its ordered segments. Accessible by any authenticated user.

**Response 200 — OK**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440001",
  "name": "Downtown Commute",
  "origin_name": "North Suburbs",
  "destination_name": "City Center",
  "total_distance_km": 15.5,
  "is_active": true,
  "segments": [
    {
      "id": "111e8400-e29b-41d4-a716-446655440001",
      "route_id": "770e8400-e29b-41d4-a716-446655440001",
      "segment_id": "660e8400-e29b-41d4-a716-446655440001",
      "sequence_order": 1
    }
  ],
  "created_at": "2025-01-15T10:30:00+00:00",
  "updated_at": "2025-01-15T10:30:00+00:00"
}
```

**Error Responses**
- `404 Not Found`: Route does not exist or was soft-deleted.

---

### `GET /api/v1/routes/{route_id}/traffic`
Get aggregated current traffic across all segments of a route. Accessible by any authenticated user.

**Response 200 — OK**
```json
{
  "route_id": "770e8400-e29b-41d4-a716-446655440001",
  "total_segments": 3,
  "segments_with_data": 3,
  "worst_congestion_level": "HEAVY",
  "average_speed_kmh": 45.2
}
```

**Error Responses**
- `404 Not Found`: Route does not exist or was soft-deleted.

---

### `POST /api/v1/routes`
Create a new route. Requires `ADMIN` role.

**Request Body**
```json
{
  "name": "Downtown Commute",
  "origin_name": "North Suburbs",
  "destination_name": "City Center",
  "total_distance_km": 15.5,
  "is_active": true
}
```

**Response 201 — Created**
Returns the newly created route object.

---

### `PUT /api/v1/routes/{route_id}`
Update a route. Requires `ADMIN` role.

**Request Body**
```json
{
  "name": "Downtown Commute Alternative",
  "is_active": false
}
```

**Response 200 — OK**
Returns the updated route.

**Error Responses**
- `404 Not Found`: Route does not exist or was soft-deleted.

---

### `POST /api/v1/routes/{route_id}/segments`
Add a traffic segment to a route at a specific sequence order. Requires `ADMIN` role.

**Request Body**
```json
{
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "sequence_order": 1
}
```

**Response 201 — Created**
Returns the `RouteSegment` association record.

**Error Responses**
- `404 Not Found`: Route or Segment does not exist.
- `409 Conflict`: Sequence order is already taken in this route.

---

### `DELETE /api/v1/routes/{route_id}/segments/{id}`
Remove a segment from a route by its RouteSegment association ID. Requires `ADMIN` role.

**Response 204 — No Content**

**Error Responses**
- `404 Not Found`: Route does not exist or Segment is not part of this route.

---

### `DELETE /api/v1/routes/{route_id}`
Soft-delete a route. Requires `ADMIN` role.

**Response 204 — No Content**

**Error Responses**
- `404 Not Found`: Route does not exist or was already soft-deleted.

---

## Module 7: Analytics

### `GET /api/v1/analytics/summary`
Get a system-wide snapshot. Accessible by any authenticated user.

**Response 200 — OK**
```json
{
  "total_active_segments": 150,
  "total_active_cameras": 120,
  "current_active_alerts": 5,
  "overall_avg_speed_kmh": 55.4,
  "timestamp": "2025-01-15T10:30:00+00:00"
}
```

---

### `GET /api/v1/analytics/congestion-heatmap`
Get all segments with their latest congestion levels. Accessible by any authenticated user.

**Response 200 — OK**
```json
[
  {
    "segment_id": "660e8400-e29b-41d4-a716-446655440001",
    "congestion_level": "MODERATE",
    "recorded_at": "2025-01-15T10:30:00+00:00",
    "latitude": 40.7128,
    "longitude": -74.0060
  }
]
```

---

### `GET /api/v1/analytics/peak-hours`
Get hourly vehicle count averages across all segments. Accessible by any authenticated user.

**Query Parameters**
- `from_dt` (datetime, optional)
- `to_dt` (datetime, optional)

**Response 200 — OK**
```json
[
  {
    "hour_of_day": 8,
    "avg_vehicle_count": 450.5
  },
  {
    "hour_of_day": 9,
    "avg_vehicle_count": 510.2
  }
]
```

**Error Responses**
- `422 Unprocessable Entity`: Invalid date range (e.g., from_dt after to_dt).

---

### `GET /api/v1/analytics/segments/{segment_id}/history`
Get historical readings for a segment aggregated by time buckets. Accessible by any authenticated user.

**Query Parameters**
- `bucket_minutes` (integer, default: 60)
- `from_dt` (datetime, optional)
- `to_dt` (datetime, optional)

**Response 200 — OK**
```json
[
  {
    "time_bucket": "2025-01-15T08:00:00+00:00",
    "avg_speed_kmh": 42.5,
    "avg_vehicle_count": 120.0,
    "max_congestion_level": "HEAVY"
  }
  }
]
```

**Error Responses**
- `404 Not Found`: Segment does not exist.
- `422 Unprocessable Entity`: Invalid bucket_minutes (allowed: 5, 15, 30, 60) or invalid date range.

---

### `GET /api/v1/analytics/segments/{segment_id}/trends`
Get statistical trends for a specific segment. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Response 200 — OK**
```json
{
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "daily_avg_vehicles": 1500,
  "daily_avg_speed_kmh": 45.5,
  "most_common_congestion": "MODERATE",
  "trend_direction": "INCREASING"
}
```

**Error Responses**
- `404 Not Found`: Segment does not exist.

---

### `GET /api/v1/analytics/predictions`
Get a prediction performance report. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Query Parameters**
- `segment_id` (UUID, optional): Filter by segment.
- `status` (string, optional): Filter by status (`PENDING`, `COMPLETED`, `FAILED`).
- `skip` (integer, default: 0)
- `limit` (integer, default: 100)

**Response 200 — OK**
```json
{
  "total_predictions": 150,
  "completed": 140,
  "failed": 5,
  "pending": 5,
  "completion_rate": 0.9333,
  "predictions": [
    {
      "id": "880e8400-e29b-41d4-a716-446655440003",
      "segment_id": "660e8400-e29b-41d4-a716-446655440001",
      "status": "COMPLETED",
      "model_version": "rf-v2-150-a1b2c3d4",
      "prediction_for": "2025-01-15T11:30:00+00:00",
      "horizon_minutes": 60,
      "predicted_congestion_level": "HEAVY",
      "predicted_vehicle_count": 120,
      "predicted_avg_speed_kmh": 35.5,
      "confidence_score": 0.85,
      "requested_at": "2025-01-15T10:30:00+00:00",
      "completed_at": "2025-01-15T10:30:05+00:00"
    }
  ]
}
```

---

### `GET /api/v1/analytics/reports`
Get a full analytics report combining multiple domains. Requires `ADMIN` or `TRAFFIC_CONTROLLER` role.

**Query Parameters**
- `from_dt` (datetime, required)
- `to_dt` (datetime, required)

**Response 200 — OK**
```json
{
  "report_period": {
    "start": "2025-01-14T00:00:00+00:00",
    "end": "2025-01-15T00:00:00+00:00"
  },
  "total_alerts_resolved": 12,
  "avg_alert_resolution_minutes": 45.5,
  "most_congested_segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "overall_system_health_score": 92.5
}
```

**Error Responses**
- `422 Unprocessable Entity`: Date range exceeds maximum allowed days or is invalid.

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
