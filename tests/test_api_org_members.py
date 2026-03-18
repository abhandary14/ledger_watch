import pytest
from apps.users.models import User

MEMBERS_URL = "/api/v1/organizations/members/"


@pytest.fixture
def admin_user(org):
    return User.objects.create_user(
        email="admin@testcorp.com",
        password="adminpass123",
        organization=org,
        role=User.Role.ADMIN,
    )


@pytest.fixture
def employee_user(org):
    return User.objects.create_user(
        email="employee@testcorp.com",
        password="emppass123",
        organization=org,
        role=User.Role.EMPLOYEE,
    )


@pytest.mark.django_db
class TestOrgMemberListAPI:
    def test_owner_can_list_members(self, auth_client, user):
        response = auth_client.get(MEMBERS_URL)
        assert response.status_code == 200

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(MEMBERS_URL)
        assert response.status_code == 401

    def test_admin_cannot_list_members(self, org, admin_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(MEMBERS_URL)
        assert response.status_code == 403

    def test_employee_cannot_list_members(self, org, employee_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=employee_user)
        response = client.get(MEMBERS_URL)
        assert response.status_code == 403

    def test_returns_only_own_org_members(self, auth_client, user, user2, org2):
        response = auth_client.get(MEMBERS_URL)
        assert response.status_code == 200
        emails = [m["email"] for m in response.data]
        assert user.email in emails
        assert user2.email not in emails

    def test_response_includes_role_field(self, auth_client, user):
        response = auth_client.get(MEMBERS_URL)
        assert response.status_code == 200
        assert "role" in response.data[0]


@pytest.mark.django_db
class TestOrgMemberCreateAPI:
    def test_owner_can_create_member(self, auth_client):
        payload = {
            "email": "newmember@testcorp.com",
            "password": "securepass123",
            "role": "employee",
        }
        response = auth_client.post(MEMBERS_URL, payload, format="json")
        assert response.status_code == 201

    def test_create_member_persists_to_db(self, auth_client, org):
        payload = {
            "email": "persisted@testcorp.com",
            "password": "securepass123",
            "role": "admin",
        }
        auth_client.post(MEMBERS_URL, payload, format="json")
        assert User.objects.filter(email="persisted@testcorp.com").exists()

    def test_created_member_belongs_to_same_org(self, auth_client, org):
        payload = {
            "email": "sameorg@testcorp.com",
            "password": "securepass123",
            "role": "employee",
        }
        auth_client.post(MEMBERS_URL, payload, format="json")
        member = User.objects.get(email="sameorg@testcorp.com")
        assert member.organization_id == org.id

    def test_owner_role_is_rejected(self, auth_client):
        payload = {
            "email": "owner2@testcorp.com",
            "password": "securepass123",
            "role": "owner",
        }
        response = auth_client.post(MEMBERS_URL, payload, format="json")
        assert response.status_code == 400

    def test_duplicate_email_returns_400(self, auth_client, user):
        payload = {
            "email": user.email,
            "password": "securepass123",
            "role": "employee",
        }
        response = auth_client.post(MEMBERS_URL, payload, format="json")
        assert response.status_code == 400

    def test_admin_cannot_create_member(self, org, admin_user):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=admin_user)
        payload = {
            "email": "blocked@testcorp.com",
            "password": "securepass123",
            "role": "employee",
        }
        response = client.post(MEMBERS_URL, payload, format="json")
        assert response.status_code == 403

    def test_unauthenticated_returns_401(self, api_client):
        payload = {
            "email": "unauth@testcorp.com",
            "password": "securepass123",
            "role": "employee",
        }
        response = api_client.post(MEMBERS_URL, payload, format="json")
        assert response.status_code == 401

    def test_create_with_name_fields(self, auth_client):
        payload = {
            "email": "named@testcorp.com",
            "password": "securepass123",
            "role": "admin",
            "first_name": "Jane",
            "last_name": "Doe",
        }
        response = auth_client.post(MEMBERS_URL, payload, format="json")
        assert response.status_code == 201
        assert response.data["first_name"] == "Jane"
        assert response.data["last_name"] == "Doe"

    def test_writes_audit_log(self, auth_client, org):
        from apps.audit.models import AuditLog
        payload = {
            "email": "audit@testcorp.com",
            "password": "securepass123",
            "role": "employee",
        }
        auth_client.post(MEMBERS_URL, payload, format="json")
        assert AuditLog.objects.filter(
            organization=org,
            event_type="USER_REGISTERED",
        ).exists()


@pytest.mark.django_db
class TestRegisterDuplicateOrgName:
    def test_duplicate_org_name_returns_400(self, api_client, org):
        payload = {
            "email": "brand_new@example.com",
            "password": "securepass123",
            "organization_name": org.name,
        }
        response = api_client.post("/api/v1/auth/register", payload, format="json")
        assert response.status_code == 400
        assert "organization_name" in response.data
