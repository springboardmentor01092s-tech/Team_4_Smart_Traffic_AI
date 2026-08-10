"""
app/schemas/camera.py

Pydantic v2 schemas for the Traffic Cameras endpoints.

Separation of concerns:
  - CameraCreate: validated request body for POST /cameras
  - CameraUpdate: validated request body for PUT /cameras/{id} (all fields optional)
  - CameraRead:   what the API returns — excludes deleted_at
  - CameraListResponse: paginated list wrapper

Validation rules applied here (Pydantic layer):
  - name: 2–100 characters
  - location_name: 2–255 characters
  - latitude: -90.0 to 90.0
  - longitude: -180.0 to 180.0
  - description: max 500 characters (validated via field_validator)
  - status: must be a valid CameraStatus enum value
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.camera import CameraStatus


class CameraCreate(BaseModel):
    """
    Request body for POST /api/v1/cameras.

    All fields are required except description and installed_at.
    Status defaults to ACTIVE if not provided.
    """

    name: str = Field(
        min_length=2,
        max_length=100,
        examples=["Highway 1 North Camera"],
        description="Human-readable label for the camera (2–100 chars).",
    )
    location_name: str = Field(
        min_length=2,
        max_length=255,
        examples=["NH-1 near Toll Plaza 3"],
        description="Textual description of the installation location (2–255 chars).",
    )
    latitude: float = Field(
        ge=-90.0,
        le=90.0,
        examples=[28.6139],
        description="Geographic latitude of the camera. Must be between -90.0 and 90.0.",
    )
    longitude: float = Field(
        ge=-180.0,
        le=180.0,
        examples=[77.2090],
        description="Geographic longitude of the camera. Must be between -180.0 and 180.0.",
    )
    status: CameraStatus = Field(
        default=CameraStatus.ACTIVE,
        examples=["ACTIVE"],
        description="Operational status of the camera.",
    )
    description: str | None = Field(
        default=None,
        examples=["Overhead gantry camera, 4K resolution"],
        description="Optional free-text notes about the camera (max 500 chars).",
    )
    installed_at: datetime | None = Field(
        default=None,
        examples=["2026-01-15T08:00:00Z"],
        description=(
            "UTC timestamp of physical installation. "
            "Defaults to the current UTC time if not provided."
        ),
    )

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("description must not exceed 500 characters.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Highway 1 North Camera",
                "location_name": "NH-1 near Toll Plaza 3",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "status": "ACTIVE",
                "description": "Overhead gantry camera, 4K resolution",
            }
        }
    }


class CameraUpdate(BaseModel):
    """
    Request body for PUT /api/v1/cameras/{camera_id}.

    All fields are optional. Only provided (non-None) fields are written
    to the database. At least one field should be supplied.
    """

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Highway 1 North Camera v2"],
        description="Updated camera label.",
    )
    location_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        examples=["NH-1 near Toll Plaza 4"],
        description="Updated installation location description.",
    )
    latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Updated geographic latitude.",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Updated geographic longitude.",
    )
    status: CameraStatus | None = Field(
        default=None,
        examples=["MAINTENANCE"],
        description="Updated operational status.",
    )
    description: str | None = Field(
        default=None,
        examples=["Upgraded to 8K resolution"],
        description="Updated notes (max 500 chars).",
    )
    installed_at: datetime | None = Field(
        default=None,
        description="Updated installation timestamp.",
    )

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("description must not exceed 500 characters.")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "MAINTENANCE",
                "description": "Under scheduled inspection",
            }
        }
    }


class CameraRead(BaseModel):
    """
    Response schema returned for any camera endpoint.

    deleted_at is intentionally excluded — soft-deleted cameras are
    invisible to API consumers.
    """

    id: uuid.UUID
    name: str
    location_name: str
    latitude: float
    longitude: float
    status: CameraStatus
    description: str | None
    installed_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "Highway 1 North Camera",
                "location_name": "NH-1 near Toll Plaza 3",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "status": "ACTIVE",
                "description": "Overhead gantry camera, 4K resolution",
                "installed_at": "2026-01-15T08:00:00Z",
                "created_at": "2026-01-15T08:00:00Z",
                "updated_at": "2026-01-15T08:00:00Z",
            }
        },
    }
