from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class LandRecordHolder:
    """A right-holder returned by an authorized land-record source."""

    holder_reference: str
    holder_type: str
    display_name: str
    interest_type: str
    share_percentage: Decimal | None = None


@dataclass(frozen=True)
class LandRecordResult:
    """Normalized result returned by a land-record provider."""

    found: bool
    provider: str
    source_system: str
    source_record_reference: str | None
    source_version: str | None
    retrieved_at: datetime
    holders: tuple[LandRecordHolder, ...] = ()


class LandRecordProvider(ABC):
    """Contract implemented by every land-record provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable provider identifier."""
        raise NotImplementedError

    @abstractmethod
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
        """Retrieve recorded right-holder information for a parcel."""
        raise NotImplementedError