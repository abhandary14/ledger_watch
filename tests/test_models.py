import pytest
from decimal import Decimal
from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError

from apps.organizations.models import Organization
from apps.transactions.models import Transaction
from apps.analytics.models import AnalysisRun
from apps.audit.models import AuditLog


@pytest.mark.django_db
class TestOrganizationModel:
    def test_creates_with_uuid_pk(self):
        org = Organization.objects.create(name="Acme Corp")
        assert org.id is not None
        assert str(org.id)
        assert org.name == "Acme Corp"

    def test_created_at_is_set_automatically(self):
        org = Organization.objects.create(name="Stamp Corp")
        assert org.created_at is not None

    def test_str_returns_name(self):
        org = Organization.objects.create(name="Baz LLC")
        assert str(org) == "Baz LLC"


@pytest.mark.django_db
class TestTransactionModel:
    def test_creates_with_all_fields(self, org):
        tx = Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="AWS",
            amount=Decimal("500.00"),
            description="Cloud hosting",
            category="SaaS",
        )
        assert tx.id is not None
        assert tx.vendor == "AWS"
        assert tx.amount == Decimal("500.00")
        assert tx.category == "SaaS"
        assert tx.created_at is not None

    def test_optional_fields_default_to_empty_string(self, org):
        tx = Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="Stripe",
            amount=Decimal("200.00"),
        )
        assert tx.description == ""
        assert tx.category == ""

    def test_clean_rejects_zero_amount(self, org):
        tx = Transaction(
            organization=org,
            date=date(2026, 1, 10),
            vendor="Bad",
            amount=Decimal("0.00"),
        )
        with pytest.raises(ValidationError):
            tx.full_clean()

    def test_clean_rejects_negative_amount(self, org):
        tx = Transaction(
            organization=org,
            date=date(2026, 1, 10),
            vendor="Bad",
            amount=Decimal("-50.00"),
        )
        with pytest.raises(ValidationError):
            tx.full_clean()

    def test_str_format(self, org):
        tx = Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="Paypal",
            amount=Decimal("99.99"),
        )
        s = str(tx)
        assert "Paypal" in s
        assert "99.99" in s


@pytest.mark.django_db
class TestAuditLogImmutability:
    def test_initial_create_succeeds(self, org):
        log = AuditLog.objects.create(
            organization=org,
            event_type="TEST_EVENT",
            metadata={"key": "value"},
        )
        assert log.id is not None

    def test_save_raises_on_update(self, org):
        log = AuditLog.objects.create(
            organization=org,
            event_type="TEST_EVENT",
            metadata={},
        )
        log.event_type = "MODIFIED"
        with pytest.raises(PermissionDenied):
            log.save()

    def test_delete_raises(self, org):
        log = AuditLog.objects.create(
            organization=org,
            event_type="TEST_EVENT",
            metadata={},
        )
        with pytest.raises(PermissionDenied):
            log.delete()


@pytest.mark.django_db
class TestAnalysisRunInvariants:
    def test_pending_rejects_results_summary(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.PENDING,
            results_summary={"some": "data"},
        )
        with pytest.raises(ValidationError):
            run.full_clean()

    def test_pending_rejects_error_message(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.PENDING,
            error_message="some error",
        )
        with pytest.raises(ValidationError):
            run.full_clean()

    def test_succeeded_requires_results_summary(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.SUCCEEDED,
            results_summary=None,
        )
        with pytest.raises(ValidationError):
            run.full_clean()

    def test_succeeded_rejects_error_message(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.SUCCEEDED,
            results_summary={"flagged": []},
            error_message="oops",
        )
        with pytest.raises(ValidationError):
            run.full_clean()

    def test_failed_requires_error_message(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.FAILED,
            error_message=None,
        )
        with pytest.raises(ValidationError):
            run.full_clean()

    def test_failed_rejects_results_summary(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.FAILED,
            error_message="boom",
            results_summary={"data": "here"},
        )
        with pytest.raises(ValidationError):
            run.full_clean()

    def test_valid_succeeded_passes_clean(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.SUCCEEDED,
            results_summary={"flagged": []},
        )
        run.full_clean()  # should not raise

    def test_valid_failed_passes_clean(self, org):
        run = AnalysisRun(
            organization=org,
            analysis_type="large_transaction",
            status=AnalysisRun.Status.FAILED,
            error_message="Something went wrong",
        )
        run.full_clean()  # should not raise
