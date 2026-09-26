from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.integrations.land_records.provider import (
    LandRecordHolder,
    LandRecordProvider,
    LandRecordResult,
)


class MockLandRecordProvider(LandRecordProvider):
    """Development-only land-record provider."""

    @property
    def provider_name(self) -> str:
        return "MOCK_LAND_RECORDS"

    def retrieve(
        self,
        *,
        parcel_id: UUID,
        state: str,
        district: str,
        taluka: str | None,
        village: str | None,
        survey_number: str,
        subdivision_number: str | None,
    ) -> LandRecordResult:
        retrieved_at = datetime.now(timezone.utc)

        holder = LandRecordHolder(
            holder_reference=f"MOCK-HOLDER-{survey_number}",
            holder_type="INDIVIDUAL",
            display_name=f"Recorded Holder - {survey_number}",
            interest_type="OWNER",
            share_percentage=Decimal("100.00000"),
        )

        return LandRecordResult(
            found=True,
            provider=self.provider_name,
            source_system="MOCK_LAND_RECORD_SYSTEM",
            source_record_reference=f"MOCK-{state}-{district}-{survey_number}",
            source_version="MOCK-1.0",
            retrieved_at=retrieved_at,
            holders=(holder,),
        )