import pytest


@pytest.fixture
def base_facts() -> dict:
    """Facts shared by every eligible profile: an ST student with no other award."""
    return {
        "is_scheduled_tribe": True,
        "studies_abroad": False,
        "current_mota_award": "none",
        "holds_other_scholarship": False,
    }
