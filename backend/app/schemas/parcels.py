from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CreateParcelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parcel_reference: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    taluka: str | None = Field(default=None, max_length=100)
    village: str | None = Field(default=None, max_length=100)

    survey_number: str = Field(min_length=1, max_length=100)
    subdivision_number: str | None = Field(
        default=None,
        max_length=100,
    )

    recorded_area_sq_m: Decimal = Field(gt=0)
    surveyed_area_sq_m: Decimal | None = Field(default=None, gt=0)
    acquired_area_sq_m: Decimal | None = Field(default=None, gt=0)

    land_category: str | None = Field(
        default=None,
        max_length=100,
    )
    land_record_reference: str | None = Field(
        default=None,
        max_length=150,
    )
    source_system: str | None = Field(
        default=None,
        max_length=150,
    )

    @field_validator(
        "parcel_reference",
        "state",
        "district",
        "survey_number",
        mode="before",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        normalized = value.strip()

        if not normalized:
            raise ValueError("Value cannot be empty.")

        return normalized

    @field_validator(
        "taluka",
        "village",
        "subdivision_number",
        "land_category",
        "land_record_reference",
        "source_system",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        normalized = value.strip()

        return normalized or None


class UpdateParcelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parcel_reference: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=100)
    taluka: str | None = Field(default=None, max_length=100)
    village: str | None = Field(default=None, max_length=100)

    survey_number: str = Field(min_length=1, max_length=100)
    subdivision_number: str | None = Field(
        default=None,
        max_length=100,
    )

    recorded_area_sq_m: Decimal = Field(gt=0)
    surveyed_area_sq_m: Decimal | None = Field(default=None, gt=0)
    acquired_area_sq_m: Decimal | None = Field(default=None, gt=0)

    land_category: str | None = Field(
        default=None,
        max_length=100,
    )
    land_record_reference: str | None = Field(
        default=None,
        max_length=150,
    )
    source_system: str | None = Field(
        default=None,
        max_length=150,
    )

    @field_validator(
        "parcel_reference",
        "state",
        "district",
        "survey_number",
        mode="before",
    )
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        normalized = value.strip()

        if not normalized:
            raise ValueError("Value cannot be empty.")

        return normalized

    @field_validator(
        "taluka",
        "village",
        "subdivision_number",
        "land_category",
        "land_record_reference",
        "source_system",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        normalized = value.strip()

        return normalized or None


class ParcelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parcel_reference: str

    state: str
    district: str
    taluka: str | None
    village: str | None

    survey_number: str
    subdivision_number: str | None

    recorded_area_sq_m: Decimal
    surveyed_area_sq_m: Decimal | None
    acquired_area_sq_m: Decimal | None

    land_category: str | None
    land_record_reference: str | None
    source_system: str | None

    geometry: object | None = None

    created_at: datetime
    updated_at: datetime


class ParcelListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ParcelResponse]
    total: int
    offset: int
    limit: int