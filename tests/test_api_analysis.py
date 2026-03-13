import pytest
import uuid

from apps.analytics.models import AnalysisRun


RUN_URL = "/api/v1/analysis/run"
RESULTS_URL = "/api/v1/analysis/results"


@pytest.mark.django_db
class TestAnalysisRunAPI:
    def test_valid_run_returns_201(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "analysis_type": "large_transaction",
        }
        response = api_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 201

    def test_response_contains_run_id(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "analysis_type": "large_transaction",
        }
        response = api_client.post(RUN_URL, payload, format="json")
        assert "id" in response.data

    def test_response_contains_status_succeeded(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "analysis_type": "large_transaction",
        }
        response = api_client.post(RUN_URL, payload, format="json")
        assert response.data["status"] == "SUCCEEDED"

    def test_unknown_analysis_type_returns_400(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "analysis_type": "nonexistent_analyzer",
        }
        response = api_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 400

    def test_nonexistent_org_returns_404(self, api_client):
        payload = {
            "organization_id": str(uuid.uuid4()),
            "analysis_type": "large_transaction",
        }
        response = api_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 404

    def test_missing_organization_id_returns_400(self, api_client):
        payload = {"analysis_type": "large_transaction"}
        response = api_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_analysis_type_returns_400(self, api_client, org):
        payload = {"organization_id": str(org.id)}
        response = api_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 400

    def test_creates_analysis_run_record(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "analysis_type": "burn_rate",
        }
        api_client.post(RUN_URL, payload, format="json")
        assert AnalysisRun.objects.filter(
            organization=org, analysis_type="burn_rate"
        ).exists()


@pytest.mark.django_db
class TestAnalysisResultsAPI:
    def test_returns_200(self, api_client):
        response = api_client.get(RESULTS_URL)
        assert response.status_code == 200

    def test_returns_list_of_runs(self, api_client, org):
        api_client.post(
            RUN_URL,
            {"organization_id": str(org.id), "analysis_type": "large_transaction"},
            format="json",
        )
        response = api_client.get(RESULTS_URL)
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 1

    def test_filter_by_organization_id(self, api_client, org, org2):
        api_client.post(
            RUN_URL,
            {"organization_id": str(org.id), "analysis_type": "large_transaction"},
            format="json",
        )
        api_client.post(
            RUN_URL,
            {"organization_id": str(org2.id), "analysis_type": "large_transaction"},
            format="json",
        )
        response = api_client.get(RESULTS_URL, {"organization_id": str(org.id)})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for run in results:
            assert str(run["organization"]) == str(org.id)

    def test_filter_by_analysis_type(self, api_client, org):
        api_client.post(
            RUN_URL,
            {"organization_id": str(org.id), "analysis_type": "large_transaction"},
            format="json",
        )
        api_client.post(
            RUN_URL,
            {"organization_id": str(org.id), "analysis_type": "burn_rate"},
            format="json",
        )
        response = api_client.get(RESULTS_URL, {"analysis_type": "large_transaction"})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for run in results:
            assert run["analysis_type"] == "large_transaction"
