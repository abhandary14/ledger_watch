import pytest
from decimal import Decimal
from datetime import date, timedelta

from django.db import connection
from rest_framework.test import APIClient

from apps.organizations.models import Domain, Organization
from apps.transactions.models import Transaction
from apps.users.models import User


TEST_TENANTS = [
    ("Test Corp", "test_tenant_1"),
    ("Other Corp", "test_tenant_2"),
]


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Create the two test tenants once per session.

    Creating an Organization creates its PostgreSQL schema and runs every
    tenant migration, which is too slow to repeat per test. These rows and
    schemas are committed outside the per-test transaction; data each test
    writes inside them is still rolled back.
    """
    with django_db_blocker.unblock():
        for name, schema_name in TEST_TENANTS:
            org = Organization.objects.create(name=name, schema_name=schema_name)
            Domain.objects.create(domain=f"{schema_name}.test.local", tenant=org, is_primary=True)


@pytest.fixture(autouse=True)
def _reset_schema():
    """Start every test on the public schema, whatever the previous test left behind."""
    connection.set_schema_to_public()


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def org(db):
    """
    Return the primary test Organization and switch the connection to its schema.

    Tenant-scoped models (Transaction, Alert, AnalysisRun, AuditLog, ReportRun)
    created or queried directly in a test land in this org's schema.
    """
    org = Organization.objects.get(schema_name=TEST_TENANTS[0][1])
    connection.set_tenant(org)
    return org


@pytest.fixture
def org2(db):
    """
    Return a second Organization (for isolation tests) without switching to it.

    Write org2 data inside ``tenant_context(org2)``.
    """
    return Organization.objects.get(schema_name=TEST_TENANTS[1][1])


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
def auth_client2(user2):
    """Return an APIClient authenticated as the org2 owner."""
    client = APIClient()
    client.force_authenticate(user=user2)
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
                date=last_month - timedelta(days=i),
                vendor=f"Vendor{i}",
                amount=Decimal("100.00"),
                category="SaaS",
            )
        )
    for i in range(5):
        txs.append(
            Transaction.objects.create(
                date=this_month - timedelta(days=i),
                vendor=f"Vendor{i}",
                amount=Decimal("100.00"),
                category="SaaS",
            )
        )
    return txs
