import pytest
from decimal import Decimal
from datetime import date

from apps.transactions.models import Transaction


IMPORT_URL = "/api/v1/transactions/import"
LIST_URL = "/api/v1/transactions/"


@pytest.mark.django_db
class TestTransactionImportAPI:
    def test_valid_import_returns_201(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "transactions": [
                {
                    "date": "2026-01-10",
                    "vendor": "AWS",
                    "amount": "500.00",
                    "description": "Cloud",
                    "category": "SaaS",
                }
            ],
        }
        response = api_client.post(IMPORT_URL, payload, format="json")
        assert response.status_code == 201
        assert response.data["imported"] == 1

    def test_import_creates_transaction_in_db(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "transactions": [
                {"date": "2026-01-15", "vendor": "Stripe", "amount": "200.00"},
            ],
        }
        api_client.post(IMPORT_URL, payload, format="json")
        assert Transaction.objects.filter(organization=org, vendor="Stripe").exists()

    def test_import_multiple_transactions(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "transactions": [
                {"date": "2026-01-10", "vendor": "AWS", "amount": "100.00"},
                {"date": "2026-01-11", "vendor": "GCP", "amount": "200.00"},
                {"date": "2026-01-12", "vendor": "Azure", "amount": "300.00"},
            ],
        }
        response = api_client.post(IMPORT_URL, payload, format="json")
        assert response.status_code == 201
        assert response.data["imported"] == 3

    def test_missing_organization_id_returns_400(self, api_client):
        payload = {
            "transactions": [
                {"date": "2026-01-10", "vendor": "AWS", "amount": "100.00"},
            ]
        }
        response = api_client.post(IMPORT_URL, payload, format="json")
        assert response.status_code == 400

    def test_empty_transactions_list_returns_400(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "transactions": [],
        }
        response = api_client.post(IMPORT_URL, payload, format="json")
        assert response.status_code == 400

    def test_negative_amount_returns_400(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "transactions": [
                {"date": "2026-01-10", "vendor": "Bad", "amount": "-50.00"},
            ],
        }
        response = api_client.post(IMPORT_URL, payload, format="json")
        assert response.status_code == 400

    def test_invalid_date_format_returns_400(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "transactions": [
                {"date": "not-a-date", "vendor": "AWS", "amount": "100.00"},
            ],
        }
        response = api_client.post(IMPORT_URL, payload, format="json")
        assert response.status_code == 400

    def test_missing_vendor_returns_400(self, api_client, org):
        payload = {
            "organization_id": str(org.id),
            "transactions": [
                {"date": "2026-01-10", "amount": "100.00"},
            ],
        }
        response = api_client.post(IMPORT_URL, payload, format="json")
        assert response.status_code == 400


@pytest.mark.django_db
class TestTransactionListAPI:
    def test_returns_200(self, api_client, transactions):
        response = api_client.get(LIST_URL)
        assert response.status_code == 200

    def test_returns_paginated_results(self, api_client, transactions):
        response = api_client.get(LIST_URL)
        data = response.data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_filter_by_vendor(self, api_client, org):
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 10),
            vendor="FilterMe", amount=Decimal("100.00")
        )
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 11),
            vendor="OtherVendor", amount=Decimal("200.00")
        )
        response = api_client.get(LIST_URL, {"vendor": "FilterMe"})
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) >= 1
        assert all(tx["vendor"] == "FilterMe" for tx in results)

    def test_filter_by_category(self, api_client, org):
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 10),
            vendor="Payroll", amount=Decimal("5000.00"), category="Payroll"
        )
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 11),
            vendor="AWS", amount=Decimal("200.00"), category="SaaS"
        )
        response = api_client.get(LIST_URL, {"category": "Payroll"})
        assert response.status_code == 200
        results = response.data["results"]
        assert all(tx["category"] == "Payroll" for tx in results)

    def test_filter_by_date_from(self, api_client, org):
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 5),
            vendor="Early", amount=Decimal("100.00")
        )
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 20),
            vendor="Late", amount=Decimal("200.00")
        )
        response = api_client.get(LIST_URL, {"date_from": "2026-01-15"})
        assert response.status_code == 200
        results = response.data["results"]
        for tx in results:
            assert tx["date"] >= "2026-01-15"

    def test_filter_by_date_to(self, api_client, org):
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 5),
            vendor="Early", amount=Decimal("100.00")
        )
        Transaction.objects.create(
            organization=org, date=date(2026, 1, 20),
            vendor="Late", amount=Decimal("200.00")
        )
        response = api_client.get(LIST_URL, {"date_to": "2026-01-10"})
        assert response.status_code == 200
        results = response.data["results"]
        for tx in results:
            assert tx["date"] <= "2026-01-10"
