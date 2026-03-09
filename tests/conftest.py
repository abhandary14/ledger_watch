import pytest


@pytest.fixture
def api_client():
    """Return a DRF APIClient for use in tests."""
    from rest_framework.test import APIClient
    return APIClient()
