import pytest
from decimal import Decimal
from datetime import date, timedelta

from rest_framework.test import APIClient

from apps.organizations.models import Organization
from apps.transactions.models import Transaction
from apps.users.models import User


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def org(db):
    """Return a saved Organization instance."""
    return Organization.objects.create(name="Test Corp")


@pytest.fixture
def org2(db):
    """Return a second saved Organization instance (for isolation tests)."""
    return Organization.objects.create(name="Other Corp")


@pytest.fixture
def user(org):
    """Return an owner User linked to org."""
    return User.objects.create_user(
        email="owner@testcorp.com",
        password="testpassword123",
        organization=org,
        role=User.Role.OWNER,
    )


@pytest.fixture
def user2(org2):
    """Return an owner User linked to org2."""
    return User.objects.create_user(
        email="owner@othercorp.com",
        password="testpassword123",
        organization=org2,
        role=User.Role.OWNER,
    )


@pytest.fixture
def auth_client(user):
    """Return an APIClient authenticated as the org owner."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def transactions(org):
    """
    Create a set of normal-sized transactions spread over two months so
    analyzer fixtures that need multi-month data work out of the box.
    """
    last_month = date(2026, 1, 15)
    this_month = date(2026, 2, 15)
    txs = []
    for i in range(5):
        txs.append(
            Transaction.objects.create(
                organization=org,
                date=last_month - timedelta(days=i),
                vendor=f"Vendor{i}",
                amount=Decimal("100.00"),
                category="SaaS",
            )
        )
    for i in range(5):
        txs.append(
            Transaction.objects.create(
                organization=org,
                date=this_month - timedelta(days=i),
                vendor=f"Vendor{i}",
                amount=Decimal("100.00"),
                category="SaaS",
            )
        )
    return txs
