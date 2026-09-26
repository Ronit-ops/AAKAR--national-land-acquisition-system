from app.integrations.land_records.mock_provider import (
    MockLandRecordProvider,
)
from app.integrations.land_records.provider import (
    LandRecordProvider,
)


def get_land_record_provider() -> LandRecordProvider:
    """
    Return the configured land-record provider.

    Development currently uses the mock provider.
    An authorized government/provider implementation can replace
    this resolver later without changing the API contract.
    """
    return MockLandRecordProvider()