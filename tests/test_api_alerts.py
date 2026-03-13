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
    def test_returns_200(self, api_client):
        response = api_client.get(ALERTS_URL)
        assert response.status_code == 200

    def test_returns_alert_in_list(self, api_client, open_alert):
        response = api_client.get(ALERTS_URL)
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        alert_ids = [str(a["id"]) for a in results]
        assert str(open_alert.id) in alert_ids

    def test_filter_by_organization_id(self, api_client, org, org2, open_alert):
        Alert.objects.create(
            organization=org2,
            alert_type="burn_rate",
            severity=Alert.Severity.LOW,
            message="Org2 alert",
        )
        response = api_client.get(ALERTS_URL, {"organization_id": str(org.id)})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for alert in results:
            assert str(alert["organization"]) == str(org.id)

    def test_filter_by_severity(self, api_client, org):
        Alert.objects.create(
            organization=org, alert_type="large_transaction",
            severity=Alert.Severity.HIGH, message="High alert"
        )
        Alert.objects.create(
            organization=org, alert_type="duplicate",
            severity=Alert.Severity.LOW, message="Low alert"
        )
        response = api_client.get(ALERTS_URL, {"severity": "HIGH"})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for alert in results:
            assert alert["severity"] == "HIGH"

    def test_filter_by_status(self, api_client, org, open_alert):
        Alert.objects.create(
            organization=org,
            alert_type="burn_rate",
            severity=Alert.Severity.MEDIUM,
            message="Resolved alert",
            status=Alert.Status.RESOLVED,
        )
        response = api_client.get(ALERTS_URL, {"status": "OPEN"})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for alert in results:
            assert alert["status"] == "OPEN"


@pytest.mark.django_db
class TestAlertAcknowledgeAPI:
    def test_acknowledge_open_alert_returns_200(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        response = api_client.post(url, format="json")
        assert response.status_code == 200

    def test_acknowledge_updates_status_to_acknowledged(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        api_client.post(url, format="json")
        open_alert.refresh_from_db()
        assert open_alert.status == Alert.Status.ACKNOWLEDGED

    def test_acknowledge_returns_updated_alert_data(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/acknowledge"
        response = api_client.post(url, format="json")
        assert response.data["status"] == "ACKNOWLEDGED"
        assert str(response.data["id"]) == str(open_alert.id)

    def test_acknowledge_already_acknowledged_returns_409(self, api_client, org):
        alert = Alert.objects.create(
            organization=org,
            alert_type="duplicate",
            severity=Alert.Severity.LOW,
            message="Already acked",
            status=Alert.Status.ACKNOWLEDGED,
        )
        url = f"/api/v1/alerts/{alert.id}/acknowledge"
        response = api_client.post(url, format="json")
        assert response.status_code == 409

    def test_acknowledge_nonexistent_alert_returns_404(self, api_client):
        url = f"/api/v1/alerts/{uuid.uuid4()}/acknowledge"
        response = api_client.post(url, format="json")
        assert response.status_code == 404


@pytest.mark.django_db
class TestAlertResolveAPI:
    def test_resolve_open_alert_returns_200(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/resolve"
        response = api_client.post(url, format="json")
        assert response.status_code == 200

    def test_resolve_updates_status_to_resolved(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/resolve"
        api_client.post(url, format="json")
        open_alert.refresh_from_db()
        assert open_alert.status == Alert.Status.RESOLVED

    def test_resolve_acknowledged_alert_returns_200(self, api_client, org):
        alert = Alert.objects.create(
            organization=org,
            alert_type="vendor_spike",
            severity=Alert.Severity.MEDIUM,
            message="Acked alert",
            status=Alert.Status.ACKNOWLEDGED,
        )
        url = f"/api/v1/alerts/{alert.id}/resolve"
        response = api_client.post(url, format="json")
        assert response.status_code == 200
        alert.refresh_from_db()
        assert alert.status == Alert.Status.RESOLVED

    def test_resolve_already_resolved_returns_409(self, api_client, org):
        alert = Alert.objects.create(
            organization=org,
            alert_type="burn_rate",
            severity=Alert.Severity.HIGH,
            message="Already resolved",
            status=Alert.Status.RESOLVED,
        )
        url = f"/api/v1/alerts/{alert.id}/resolve"
        response = api_client.post(url, format="json")
        assert response.status_code == 409

    def test_resolve_returns_updated_alert_data(self, api_client, open_alert):
        url = f"/api/v1/alerts/{open_alert.id}/resolve"
        response = api_client.post(url, format="json")
        assert response.data["status"] == "RESOLVED"

    def test_resolve_nonexistent_alert_returns_404(self, api_client):
        url = f"/api/v1/alerts/{uuid.uuid4()}/resolve"
        response = api_client.post(url, format="json")
        assert response.status_code == 404
