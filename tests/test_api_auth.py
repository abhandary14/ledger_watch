import pytest

from apps.organizations.models import Organization
from apps.users.models import User


REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"
REFRESH_URL = "/api/v1/auth/token/refresh"


@pytest.mark.django_db
class TestRegisterAPI:
    def test_register_returns_201(self, api_client):
        payload = {
            "email": "new@example.com",
            "password": "securepass123",
            "organization_name": "New Corp",
        }
        response = api_client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 201

    def test_register_returns_tokens(self, api_client):
        payload = {
            "email": "tokens@example.com",
            "password": "securepass123",
            "organization_name": "Token Corp",
        }
        response = api_client.post(REGISTER_URL, payload, format="json")
        assert "access" in response.data
        assert "refresh" in response.data

    def test_register_returns_user_info(self, api_client):
        payload = {
            "email": "info@example.com",
            "password": "securepass123",
            "organization_name": "Info Corp",
        }
        response = api_client.post(REGISTER_URL, payload, format="json")
        assert response.data["user"]["email"] == "info@example.com"
        assert "organization_id" in response.data["user"]

    def test_register_creates_organization(self, api_client):
        payload = {
            "email": "orgtest@example.com",
            "password": "securepass123",
            "organization_name": "Brand New Org",
        }
        api_client.post(REGISTER_URL, payload, format="json")
        assert Organization.objects.filter(name="Brand New Org").exists()

    def test_register_owner_email_creates_owner_user(self, api_client):
        payload = {
            "email": "owner@example.com",
            "password": "securepass123",
            "organization_name": "Owner Org",
        }
        api_client.post(REGISTER_URL, payload, format="json")
        user = User.objects.get(email="owner@example.com")
        assert user.role == User.Role.OWNER

    def test_register_non_owner_email_creates_employee_user(self, api_client):
        payload = {
            "email": "john@example.com",
            "password": "securepass123",
            "organization_name": "Employee Org",
        }
        api_client.post(REGISTER_URL, payload, format="json")
        user = User.objects.get(email="john@example.com")
        assert user.role == User.Role.EMPLOYEE

    def test_duplicate_email_returns_400(self, api_client, user):
        payload = {
            "email": user.email,
            "password": "securepass123",
            "organization_name": "Duplicate Corp",
        }
        response = api_client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_short_password_returns_400(self, api_client):
        payload = {
            "email": "short@example.com",
            "password": "short",
            "organization_name": "Short Corp",
        }
        response = api_client.post(REGISTER_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_fields_returns_400(self, api_client):
        response = api_client.post(REGISTER_URL, {"email": "x@x.com"}, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestLoginAPI:
    def test_valid_credentials_returns_200(self, api_client, user):
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "testpassword123"},
            format="json",
        )
        assert response.status_code == 200

    def test_login_returns_tokens(self, api_client, user):
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "testpassword123"},
            format="json",
        )
        assert "access" in response.data
        assert "refresh" in response.data

    def test_wrong_password_returns_401(self, api_client, user):
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code == 401

    def test_unknown_email_returns_401(self, api_client):
        response = api_client.post(
            LOGIN_URL,
            {"email": "nobody@example.com", "password": "anypassword"},
            format="json",
        )
        assert response.status_code == 401

    def test_wrong_and_unknown_return_same_message(self, api_client, user):
        """No user enumeration — both failure cases return the same detail."""
        wrong_pw = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "wrongpassword"},
            format="json",
        )
        unknown = api_client.post(
            LOGIN_URL,
            {"email": "nobody@example.com", "password": "anypassword"},
            format="json",
        )
        assert wrong_pw.data["detail"] == unknown.data["detail"]


@pytest.mark.django_db
class TestTokenRefreshAPI:
    def test_refresh_returns_new_access_token(self, api_client, user):
        login_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "testpassword123"},
            format="json",
        )
        refresh_token = login_response.data["refresh"]
        response = api_client.post(REFRESH_URL, {"refresh": refresh_token}, format="json")
        assert response.status_code == 200
        assert "access" in response.data

    def test_invalid_refresh_token_returns_401(self, api_client):
        response = api_client.post(REFRESH_URL, {"refresh": "invalidtoken"}, format="json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestMeAPI:
    def test_returns_200_when_authenticated(self, auth_client):
        response = auth_client.get(ME_URL)
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(ME_URL)
        assert response.status_code == 401

    def test_returns_user_and_org_data(self, auth_client, user, org):
        response = auth_client.get(ME_URL)
        assert response.data["email"] == user.email
        assert response.data["organization"]["id"] == str(org.id)
        assert response.data["organization"]["name"] == org.name

    def test_returns_role(self, auth_client, user):
        response = auth_client.get(ME_URL)
        assert response.data["role"] == User.Role.OWNER


@pytest.mark.django_db
class TestLogoutAPI:
    def test_logout_returns_204(self, api_client, user):
        login_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "testpassword123"},
            format="json",
        )
        refresh_token = login_response.data["refresh"]
        api_client.force_authenticate(user=user)
        response = api_client.post(LOGOUT_URL, {"refresh": refresh_token}, format="json")
        assert response.status_code == 204

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.post(LOGOUT_URL, {"refresh": "sometoken"}, format="json")
        assert response.status_code == 401
