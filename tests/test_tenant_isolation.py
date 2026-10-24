"""
Cross-tenant isolation tests.

Each Organization has its own PostgreSQL schema. These tests prove that one
org cannot read or modify another org's data — not even by guessing its UUID —
because the row simply does not exist in the requesting user's schema.

``auth_client`` acts as the owner of ``org``; ``auth_client2`` as the owner of ``org2``.
"""

import pytest
from datetime import date
from decimal import Decimal

from django.db import connection
from django_tenants.utils import schema_context, tenant_context

from apps.alerts.models import Alert
from apps.analytics.models import AnalysisRun
from apps.audit.models import AuditLog
from apps.transactions.models import Transaction

TENANT_TABLES = [
    "transactions_transaction",
    "alerts_alert",
    "analytics_analysisrun",
    "audit_auditlog",
    "reports_reportrun",
]


@pytest.fixture
def org_transaction(org):
    return Transaction.objects.create(
        date=date(2026, 1, 10), vendor="PrivateVendor", amount=Decimal("123.45")
    )


@pytest.fixture
def org_alert(org):
    return Alert.objects.create(
        alert_type="large_transaction",
        severity=Alert.Severity.HIGH,
        message="Private alert",
        status=Alert.Status.OPEN,
    )


@pytest.fixture
def org_run(org):
    return AnalysisRun.objects.create(
        analysis_type="large_transaction",
        status=AnalysisRun.Status.SUCCEEDED,
        results_summary={"analyzer": "large_transaction"},
    )


@pytest.mark.django_db
class TestSchemaLayout:
    def test_tenant_tables_do_not_exist_in_public_schema(self):
        with schema_context("public"):
            public_tables = connection.introspection.table_names()
        for table in TENANT_TABLES:
            assert table not in public_tables

    def test_tenant_tables_exist_in_each_tenant_schema(self, org, org2):
        for tenant in (org, org2):
            with tenant_context(tenant):
                tables = connection.introspection.table_names()
            for table in TENANT_TABLES:
                assert table in tables

    def test_orm_queries_only_see_active_schema(self, org, org2, org_transaction):
        assert Transaction.objects.filter(id=org_transaction.id).exists()
        with tenant_context(org2):
            assert Transaction.objects.count() == 0


@pytest.mark.django_db
class TestCrossTenantAPIAccess:
    def test_cannot_read_other_orgs_transaction(self, auth_client2, org_transaction):
        response = auth_client2.get(f"/api/v1/transactions/{org_transaction.id}/")
        assert response.status_code == 404

    def test_cannot_delete_other_orgs_transaction(self, auth_client2, org, org_transaction):
        response = auth_client2.delete(f"/api/v1/transactions/{org_transaction.id}/delete")
        assert response.status_code == 404
        with tenant_context(org):
            assert Transaction.objects.filter(id=org_transaction.id).exists()

    def test_cannot_list_other_orgs_transactions(self, auth_client2, org_transaction):
        response = auth_client2.get("/api/v1/transactions/")
        assert response.status_code == 200
        assert response.data["count"] == 0

    def test_filter_options_exclude_other_orgs_vendors(self, auth_client2, org_transaction):
        response = auth_client2.get("/api/v1/transactions/filter-options/")
        assert response.status_code == 200
        assert "PrivateVendor" not in response.data["vendors"]

    @pytest.mark.parametrize("action", ["acknowledge", "resolve"])
    def test_cannot_change_other_orgs_alert(self, auth_client2, org, org_alert, action):
        response = auth_client2.post(f"/api/v1/alerts/{org_alert.id}/{action}", format="json")
        assert response.status_code == 404
        with tenant_context(org):
            org_alert.refresh_from_db()
        assert org_alert.status == Alert.Status.OPEN

    def test_cannot_delete_other_orgs_alert(self, auth_client2, org, org_alert):
        response = auth_client2.delete(f"/api/v1/alerts/{org_alert.id}/delete")
        assert response.status_code == 404
        with tenant_context(org):
            assert Alert.objects.filter(id=org_alert.id).exists()

    def test_cannot_read_other_orgs_analysis_run(self, auth_client2, org_run):
        response = auth_client2.get(f"/api/v1/analysis/results/{org_run.id}/")
        assert response.status_code == 404

    def test_import_lands_only_in_callers_schema(self, auth_client, auth_client2, org, org2):
        payload = {"transactions": [{"date": "2026-01-10", "vendor": "Org2Only", "amount": "10.00"}]}
        response = auth_client2.post("/api/v1/transactions/import", payload, format="json")
        assert response.status_code == 201
        with tenant_context(org2):
            assert Transaction.objects.filter(vendor="Org2Only").exists()
        with tenant_context(org):
            assert not Transaction.objects.filter(vendor="Org2Only").exists()

    def test_audit_log_written_only_in_callers_schema(self, auth_client2, org, org2):
        payload = {"transactions": [{"date": "2026-01-10", "vendor": "AuditCheck", "amount": "10.00"}]}
        auth_client2.post("/api/v1/transactions/import", payload, format="json")
        with tenant_context(org2):
            assert AuditLog.objects.filter(event_type="TRANSACTION_IMPORTED").exists()
        with tenant_context(org):
            assert not AuditLog.objects.filter(event_type="TRANSACTION_IMPORTED").exists()
