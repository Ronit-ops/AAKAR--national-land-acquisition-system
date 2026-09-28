from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SurveyRecordBase(BaseModel):
    acquisition_case_id: UUID
    parcel_id: UUID
    survey_reference: str = Field(
        min_length=1,
        max_length=100,
    )
    survey_type: str = Field(
        min_length=1,
        max_length=40,
    )
    survey_method: str = Field(
        min_length=1,
        max_length=40,
    )
    scheduled_at: datetime | None = None
    surveyor_user_id: UUID | None = None
    recorded_area_sq_m: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=4,
    )
    notes: str | None = None


class SurveyRecordCreateRequest(SurveyRecordBase):
    pass


class SurveyRecordStartRequest(BaseModel):
    surveyor_user_id: UUID | None = None


class SurveyRecordCompleteRequest(BaseModel):
    measured_area_sq_m: Decimal = Field(
        gt=0,
        max_digits=18,
        decimal_places=4,
    )
    conducted_at: datetime | None = None
    notes: str | None = None


class SurveyRecordVerifyRequest(BaseModel):
    verified_at: datetime | None = None


class SurveyRecordCancelRequest(BaseModel):
    reason: str = Field(
        min_length=1,
        max_length=1000,
    )


class SurveyRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    acquisition_case_id: UUID
    parcel_id: UUID
    survey_reference: str
    survey_type: str
    survey_method: str
    status: str

    scheduled_at: datetime | None
    conducted_at: datetime | None

    surveyor_user_id: UUID | None
    verified_by_user_id: UUID | None
    verified_at: datetime | None

    recorded_area_sq_m: Decimal
    measured_area_sq_m: Decimal | None
    area_difference_sq_m: Decimal | None
    area_difference_percentage: Decimal | None

    notes: str | None

    created_at: datetime
    updated_at: datetime


class SurveyRecordListResponse(BaseModel):
    items: list[SurveyRecordResponse]
    total: int
    offset: int
    limit: int