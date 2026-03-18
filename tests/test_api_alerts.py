import pytest
import uuid

from apps.alerts.models import Alert


ALERTS_URL = "/api/v1/alerts/"


@pytest.fixture
def open_alert(org):
    return Alert.objects.create(
        organization=org,
        alert_type="large_transaction",
        severity=Alert.Severity.HIGH,
        message="Test alert",
        status=Alert.Status.OPEN,
    )


@pytest.mark.django_db
class TestAlertListAPI:
    def test_returns_200(self, auth_client):
        response = auth_client.get(ALERTS_URL)
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(ALERTS_URL)
        assert response.status_code == 401

    def test_returns_alert_in_list(self, auth_client, open_alert):
        response = auth_client.get(ALERTS_URL)
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        alert_ids = [str(a["id"]) for a in results]
        assert str(open_alert.id) in alert_ids

    def test_only_returns_own_org_alerts(self, auth_client, user2, org2, open_alert):
        Alert.objects.create(
            organization=org2,
            alert_type="burn_rate",
            severity=Alert.Severity.LOW,
            message="Org2 alert",
        )
        response = auth_client.get(ALERTS_URL)
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for alert in results:
            assert alert["message"] != "Org2 alert"

    def test_filter_by_severity(self, auth_client, org):
        Alert.objects.create(
            organization=org, alert_type="large_transaction",
            severity=Alert.Severity.HIGH, message="High alert"
        )
        Alert.objects.create(
            organization=org, alert_type="duplicate",
            severity=Alert.Severity.LOW, message="Low alert"
        )
        response = auth_client.get(ALERTS_URL, {"severity": "HIGH"})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for alert in results:
            assert alert["severity"] == "HIGH"

    def test_filter_by_status(self, auth_client, org, open_alert):
        Alert.objects.create(
            organization=org,
            alert_type="burn_rate",
            severity=Alert.Severity.MEDIUM,
            message="Resolved alert",
            status=Alert.Status.RESOLVED,
        )
        response = auth_client.get(ALERTS_URL, {"status": "OPEN"})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for alert in results:
            assert alert["status"] == "OPEN"


@pytest.mark.django_db
class TestAlertAcknowledgeAPI:
    def test_acknowledge_open_alert_returns_200(self, auth_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        response = auth_client.post(url, format="json")
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        response = api_client.post(url, format="json")
        assert response.status_code == 401

    def test_employee_cannot_acknowledge(self, org, open_alert):
        from apps.users.models import User
        from rest_framework.test import APIClient

        employee = User.objects.create_user(
            email="employee@testcorp.com",
            password="testpassword123",
            organization=org,
            role=User.Role.EMPLOYEE,
        )
        client = APIClient()
        client.force_authenticate(user=employee)
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        response = client.post(url, format="json")
        assert response.status_code == 403

    def test_acknowledge_updates_status_to_acknowledged(self, auth_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        auth_client.post(url, format="json")
        open_alert.refresh_from_db()
        assert open_alert.status == Alert.Status.ACKNOWLEDGED

    def test_acknowledge_returns_updated_alert_data(self, auth_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        response = auth_client.post(url, format="json")
        assert response.data["status"] == "ACKNOWLEDGED"
        assert str(response.data["id"]) == str(open_alert.id)

    def test_acknowledge_already_acknowledged_returns_409(self, auth_client, org):
        alert = Alert.objects.create(
            organization=org,
            alert_type="duplicate",
            severity=Alert.Severity.LOW,
            message="Already acked",
            status=Alert.Status.ACKNOWLEDGED,
        )
        url = f"/api/v1/alerts/{alert.id}/acknowledge"
        response = auth_client.post(url, format="json")
        assert response.status_code == 409

    def test_acknowledge_nonexistent_alert_returns_404(self, auth_client):
        url = f"/api/v1/alerts/{uuid.uuid4()}/acknowledge"
        response = auth_client.post(url, format="json")
        assert response.status_code == 404


@pytest.mark.django_db
class TestAlertResolveAPI:
    def test_resolve_open_alert_returns_200(self, auth_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/resolve"
        response = auth_client.post(url, format="json")
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/resolve"
        response = api_client.post(url, format="json")
        assert response.status_code == 401

    def test_resolve_updates_status_to_resolved(self, auth_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/resolve"
        auth_client.post(url, format="json")
        open_alert.refresh_from_db()
        assert open_alert.status == Alert.Status.RESOLVED

    def test_resolve_acknowledged_alert_returns_200(self, auth_client, org):
        alert = Alert.objects.create(
            organization=org,
            alert_type="vendor_spike",
            severity=Alert.Severity.MEDIUM,
            message="Acked alert",
            status=Alert.Status.ACKNOWLEDGED,
        )
        url = f"/api/v1/alerts/{alert.id}/resolve"
        response = auth_client.post(url, format="json")
        assert response.status_code == 200
        alert.refresh_from_db()
        assert alert.status == Alert.Status.RESOLVED

    def test_resolve_already_resolved_returns_409(self, auth_client, org):
        alert = Alert.objects.create(
            organization=org,
            alert_type="burn_rate",
            severity=Alert.Severity.HIGH,
            message="Already resolved",
            status=Alert.Status.RESOLVED,
        )
        url = f"/api/v1/alerts/{alert.id}/resolve"
        response = auth_client.post(url, format="json")
        assert response.status_code == 409

    def test_resolve_returns_updated_alert_data(self, auth_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/resolve"
        response = auth_client.post(url, format="json")
        assert response.data["status"] == "RESOLVED"

    def test_resolve_nonexistent_alert_returns_404(self, auth_client):
        url = f"/api/v1/alerts/{uuid.uuid4()}/resolve"
        response = auth_client.post(url, format="json")
        assert response.status_code == 404


@pytest.fixture
def resolved_alert(org):
    return Alert.objects.create(
        organization=org,
        alert_type="burn_rate",
        severity=Alert.Severity.HIGH,
        message="Resolved test alert",
        status=Alert.Status.RESOLVED,
    )


@pytest.mark.django_db
class TestAlertReopenAPI:
    def test_reopen_resolved_alert_returns_200(self, auth_client, resolved_alert):
        url = f"/api/v1/alerts/{resolved_alert.id}/reopen"
        response = auth_client.post(url, format="json")
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, api_client, resolved_alert):
        url = f"/api/v1/alerts/{resolved_alert.id}/reopen"
        response = api_client.post(url, format="json")
        assert response.status_code == 401

    def test_employee_cannot_reopen(self, org, resolved_alert):
        from apps.users.models import User
        from rest_framework.test import APIClient

        employee = User.objects.create_user(
            email="employee2@testcorp.com",
            password="testpassword123",
            organization=org,
            role=User.Role.EMPLOYEE,
        )
        client = APIClient()
        client.force_authenticate(user=employee)
        url = f"/api/v1/alerts/{resolved_alert.id}/reopen"
        response = client.post(url, format="json")
        assert response.status_code == 403

    def test_reopen_updates_status_to_open(self, auth_client, resolved_alert):
        url = f"/api/v1/alerts/{resolved_alert.id}/reopen"
        auth_client.post(url, format="json")
        resolved_alert.refresh_from_db()
        assert resolved_alert.status == Alert.Status.OPEN

    def test_reopen_returns_updated_alert_data(self, auth_client, resolved_alert):
        url = f"/api/v1/alerts/{resolved_alert.id}/reopen"
        response = auth_client.post(url, format="json")
        assert response.data["status"] == "OPEN"
        assert str(response.data["id"]) == str(resolved_alert.id)

    def test_reopen_open_alert_returns_409(self, auth_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/reopen"
        response = auth_client.post(url, format="json")
        assert response.status_code == 409

    def test_reopen_acknowledged_alert_returns_409(self, auth_client, org):
        alert = Alert.objects.create(
            organization=org,
            alert_type="duplicate",
            severity=Alert.Severity.LOW,
            message="Acked alert",
            status=Alert.Status.ACKNOWLEDGED,
        )
        url = f"/api/v1/alerts/{alert.id}/reopen"
        response = auth_client.post(url, format="json")
        assert response.status_code == 409

    def test_reopen_nonexistent_alert_returns_404(self, auth_client):
        url = f"/api/v1/alerts/{uuid.uuid4()}/reopen"
        response = auth_client.post(url, format="json")
        assert response.status_code == 404

    def test_reopen_writes_audit_log(self, auth_client, resolved_alert):
        from apps.audit.models import AuditLog

        url = f"/api/v1/alerts/{resolved_alert.id}/reopen"
        auth_client.post(url, format="json")
        assert AuditLog.objects.filter(
            organization=resolved_alert.organization,
            event_type="ALERT_REOPENED",
            metadata__alert_id=str(resolved_alert.id),
        ).exists()
