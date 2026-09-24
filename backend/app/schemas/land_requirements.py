from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LandRequirementResponse(BaseModel):
    """Public Land Requirement representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    requirement_reference: str
    purpose: str
    required_area_sq_m: Decimal
    state: str
    district: str
    taluka: str | None
    village: str | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class LandRequirementListResponse(BaseModel):
    """Paginated Land Requirement response."""

    items: list[LandRequirementResponse]
    total: int
    offset: int
    limit: int


class CreateLandRequirementRequest(BaseModel):
    """Request body for creating a Land Requirement."""

    project_id: UUID

    requirement_reference: str = Field(
        min_length=1,
        max_length=80,
    )

    purpose: str = Field(
        min_length=1,
        max_length=500,
    )

    required_area_sq_m: Decimal = Field(
        gt=0,
    )

    state: str = Field(
        min_length=1,
        max_length=100,
    )

    district: str = Field(
        min_length=1,
        max_length=100,
    )

    taluka: str | None = Field(
        default=None,
        max_length=100,
    )

    village: str | None = Field(
        default=None,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )


class UpdateLandRequirementRequest(BaseModel):
    """Request body for updating an editable Land Requirement."""

    requirement_reference: str = Field(
        min_length=1,
        max_length=80,
    )

    purpose: str = Field(
        min_length=1,
        max_length=500,
    )

    required_area_sq_m: Decimal = Field(
        gt=0,
    )

    state: str = Field(
        min_length=1,
        max_length=100,
    )

    district: str = Field(
        min_length=1,
        max_length=100,
    )

    taluka: str | None = Field(
        default=None,
        max_length=100,
    )

    village: str | None = Field(
        default=None,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=5000,
    )


class LandRequirementStatusResponse(BaseModel):
    """Land Requirement lifecycle status response."""

    id: UUID
    status: str


class LandRequirementActionRequest(BaseModel):
    """Optional reason supplied during a lifecycle action."""

    reason: str | None = Field(
        default=None,
        max_length=2000,
    )