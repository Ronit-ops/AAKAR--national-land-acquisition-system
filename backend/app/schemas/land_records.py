from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LandRecordRetrievalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parcel_id: UUID
    provider: str
    source_system: str
    source_record_reference: str | None
    requested_at: datetime
    retrieved_at: datetime | None
    status: str
    source_version: str | None
    error_code: str | None