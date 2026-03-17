import pytest

from apps.analytics.models import AnalysisRun


RUN_URL = "/api/v1/analysis/run"
RESULTS_URL = "/api/v1/analysis/results"


@pytest.mark.django_db
class TestAnalysisRunAPI:
    def test_valid_run_returns_201(self, auth_client, org):
        payload = {"analysis_type": "large_transaction"}
        response = auth_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 201

    def test_response_contains_run_id(self, auth_client, org):
        payload = {"analysis_type": "large_transaction"}
        response = auth_client.post(RUN_URL, payload, format="json")
        assert "id" in response.data

    def test_response_contains_status_succeeded(self, auth_client, org):
        payload = {"analysis_type": "large_transaction"}
        response = auth_client.post(RUN_URL, payload, format="json")
        assert response.data["status"] == "SUCCEEDED"

    def test_unknown_analysis_type_returns_400(self, auth_client, org):
        payload = {"analysis_type": "nonexistent_analyzer"}
        response = auth_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self, api_client):
        payload = {"analysis_type": "large_transaction"}
        response = api_client.post(RUN_URL, payload, format="json")
        assert response.status_code == 401

    def test_missing_analysis_type_returns_400(self, auth_client, org):
        response = auth_client.post(RUN_URL, {}, format="json")
        assert response.status_code == 400

    def test_creates_analysis_run_record(self, auth_client, org):
        payload = {"analysis_type": "burn_rate"}
        auth_client.post(RUN_URL, payload, format="json")
        assert AnalysisRun.objects.filter(
            organization=org, analysis_type="burn_rate"
        ).exists()

    def test_employee_cannot_trigger_analysis(self, org):
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
        response = client.post(RUN_URL, {"analysis_type": "large_transaction"}, format="json")
        assert response.status_code == 403


@pytest.mark.django_db
class TestAnalysisResultsAPI:
    def test_returns_200(self, auth_client):
        response = auth_client.get(RESULTS_URL)
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(RESULTS_URL)
        assert response.status_code == 401

    def test_returns_list_of_runs(self, auth_client, org):
        auth_client.post(
            RUN_URL,
            {"analysis_type": "large_transaction"},
            format="json",
        )
        response = auth_client.get(RESULTS_URL)
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 1

    def test_only_returns_own_org_runs(self, auth_client, user2, org, org2):
        from apps.analytics.models import AnalysisRun

        # Create a run for org2 directly
        AnalysisRun.objects.create(
            organization=org2,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.SUCCEEDED,
            results_summary={"analyzer": "large_transaction"},
        )
        # Run for org via authenticated client
        auth_client.post(RUN_URL, {"analysis_type": "large_transaction"}, format="json")

        response = auth_client.get(RESULTS_URL)
        results = response.data.get("results", response.data)
        for run in results:
            assert str(run["organization_id"]) == str(org.id)

    def test_filter_by_analysis_type(self, auth_client, org):
        auth_client.post(RUN_URL, {"analysis_type": "large_transaction"}, format="json")
        auth_client.post(RUN_URL, {"analysis_type": "burn_rate"}, format="json")
        response = auth_client.get(RESULTS_URL, {"analysis_type": "large_transaction"})
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for run in results:
            assert run["analysis_type"] == "large_transaction"
