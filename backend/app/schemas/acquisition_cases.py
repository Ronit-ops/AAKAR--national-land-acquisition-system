from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


LEGAL_FRAMEWORKS = {
    "RFCTLARR_2013",
    "SPECIAL_CENTRAL_ACT",
    "STATE_LAW",
    "OTHER",
}

LEGAL_ROUTES = {
    "RFCTLARR_STANDARD",
    "RFCTLARR_URGENT",
    "SPECIAL_ACT_ROUTE",
    "STATE_SPECIFIC_ROUTE",
    "NEGOTIATED_PURCHASE",
}

ACQUISITION_METHODS = {
    "COMPULSORY_ACQUISITION",
    "CONSENT_BASED",
    "NEGOTIATED_PURCHASE",
}

CASE_STATUSES = {
    "DRAFT",
    "ACTIVE",
    "ON_HOLD",
    "CANCELLED",
    "CLOSED",
}

CASE_STAGES = {
    "INITIATION",
    "SIA",
    "PRELIMINARY_NOTIFICATION",
    "OBJECTIONS_AND_HEARING",
    "DECLARATION",
    "R_AND_R",
    "CLAIMS_AND_ENQUIRY",
    "COMPENSATION_DETERMINATION",
    "AWARD",
    "COMPENSATION_AND_RR",
    "POSSESSION",
    "VESTING",
    "HANDOVER",
}


def _validate_enum_value(
    value: Optional[str],
    allowed_values: set[str],
    field_name: str,
) -> Optional[str]:
    if value is None:
        return None

    normalized = value.strip().upper()

    if normalized not in allowed_values:
        raise ValueError(
            f"{field_name} must be one of: "
            f"{', '.join(sorted(allowed_values))}"
        )

    return normalized


def _validate_case_number(value: str) -> str:
    value = value.strip()

    if not value:
        raise ValueError("case_number cannot be empty")

    if len(value) > 80:
        raise ValueError("case_number cannot exceed 80 characters")

    return value


def _validate_reason(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return value


class AcquisitionCaseCreate(BaseModel):
    """
    Payload used to create a new acquisition case.

    Operational status and current stage are intentionally excluded.
    They are controlled by the acquisition-case service.
    """

    model_config = ConfigDict(extra="forbid")

    land_requirement_id: UUID

    case_number: str = Field(
        min_length=1,
        max_length=80,
    )

    legal_framework: str = Field(
        default="RFCTLARR_2013",
        max_length=40,
    )

    legal_route: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    acquisition_method: str = Field(
        default="COMPULSORY_ACQUISITION",
        max_length=40,
    )

    responsible_authority_id: Optional[UUID] = None

    assigned_user_id: Optional[UUID] = None

    description: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    @field_validator("case_number")
    @classmethod
    def validate_case_number(cls, value: str) -> str:
        return _validate_case_number(value)

    @field_validator("legal_framework")
    @classmethod
    def validate_legal_framework(cls, value: str) -> str:
        normalized = _validate_enum_value(
            value,
            LEGAL_FRAMEWORKS,
            "legal_framework",
        )

        assert normalized is not None
        return normalized

    @field_validator("legal_route")
    @classmethod
    def validate_legal_route(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        return _validate_enum_value(
            value,
            LEGAL_ROUTES,
            "legal_route",
        )

    @field_validator("acquisition_method")
    @classmethod
    def validate_acquisition_method(cls, value: str) -> str:
        normalized = _validate_enum_value(
            value,
            ACQUISITION_METHODS,
            "acquisition_method",
        )

        assert normalized is not None
        return normalized

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        return _validate_reason(value)


class AcquisitionCaseUpdate(BaseModel):
    """
    Payload used to update acquisition-case metadata.

    current_stage and status cannot be changed through a normal PATCH.
    They must be changed through dedicated service commands.

    expected_version is required so concurrent updates cannot silently
    overwrite changes made by another user.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(
        ge=1,
        description="Current acquisition-case version expected by the client.",
    )

    legal_framework: Optional[str] = Field(
        default=None,
        max_length=40,
    )

    legal_route: Optional[str] = Field(
        default=None,
        max_length=50,
    )

    acquisition_method: Optional[str] = Field(
        default=None,
        max_length=40,
    )

    responsible_authority_id: Optional[UUID] = None

    assigned_user_id: Optional[UUID] = None

    description: Optional[str] = Field(
        default=None,
        max_length=5000,
    )

    @field_validator("legal_framework")
    @classmethod
    def validate_legal_framework(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        return _validate_enum_value(
            value,
            LEGAL_FRAMEWORKS,
            "legal_framework",
        )

    @field_validator("legal_route")
    @classmethod
    def validate_legal_route(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        return _validate_enum_value(
            value,
            LEGAL_ROUTES,
            "legal_route",
        )

    @field_validator("acquisition_method")
    @classmethod
    def validate_acquisition_method(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        return _validate_enum_value(
            value,
            ACQUISITION_METHODS,
            "acquisition_method",
        )

    @field_validator("description")
    @classmethod
    def validate_description(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        return _validate_reason(value)


class AcquisitionCaseActivate(BaseModel):
    """
    Payload used to activate a draft acquisition case.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(
        ge=1,
        description="Current acquisition-case version expected by the client.",
    )


class AcquisitionCaseHold(BaseModel):
    """
    Payload used to place an active acquisition case on hold.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(
        ge=1,
        description="Current acquisition-case version expected by the client.",
    )

    reason: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("reason cannot be empty")

        return value


class AcquisitionCaseResume(BaseModel):
    """
    Payload used to resume an acquisition case that is on hold.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(
        ge=1,
        description="Current acquisition-case version expected by the client.",
    )


class AcquisitionCaseCancel(BaseModel):
    """
    Payload used to cancel an acquisition case.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(
        ge=1,
        description="Current acquisition-case version expected by the client.",
    )

    reason: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("reason cannot be empty")

        return value


class AcquisitionCaseClose(BaseModel):
    """
    Payload used to close an acquisition case after handover.
    """

    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(
        ge=1,
        description="Current acquisition-case version expected by the client.",
    )


class AcquisitionCaseStageTransition(BaseModel):
    """
    Payload used for a controlled acquisition-case stage transition.
    """

    model_config = ConfigDict(extra="forbid")

    to_stage: str = Field(
        min_length=1,
        max_length=50,
    )

    reason: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    expected_version: int = Field(
        ge=1,
        description="Current acquisition-case version expected by the client.",
    )

    @field_validator("to_stage")
    @classmethod
    def validate_to_stage(cls, value: str) -> str:
        normalized = _validate_enum_value(
            value,
            CASE_STAGES,
            "to_stage",
        )

        assert normalized is not None
        return normalized

    @field_validator("reason")
    @classmethod
    def validate_reason(
        cls,
        value: Optional[str],
    ) -> Optional[str]:
        return _validate_reason(value)


class AcquisitionCaseStageHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    acquisition_case_id: UUID
    from_stage: Optional[str]
    to_stage: str
    reason: Optional[str]
    changed_by_user_id: Optional[UUID]
    changed_at: object


class AcquisitionCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    land_requirement_id: UUID
    case_number: str

    legal_framework: str
    legal_route: Optional[str]
    acquisition_method: str

    responsible_authority_id: Optional[UUID]
    assigned_user_id: Optional[UUID]

    status: str
    current_stage: str

    description: Optional[str]

    opened_at: Optional[object]
    closed_at: Optional[object]

    version: int

    created_at: object
    updated_at: object


class AcquisitionCaseDetail(AcquisitionCaseRead):
    stage_history: list[AcquisitionCaseStageHistoryRead] = Field(
        default_factory=list
    )


class AcquisitionCaseListItem(AcquisitionCaseRead):
    pass


class AcquisitionCaseListResponse(BaseModel):
    items: list[AcquisitionCaseListItem]
    total: int
    offset: int
    limit: int