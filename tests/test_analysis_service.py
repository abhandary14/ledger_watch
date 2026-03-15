import pytest
from decimal import Decimal
from datetime import date

from apps.transactions.models import Transaction
from apps.analytics.models import AnalysisRun
from apps.alerts.models import Alert
from apps.audit.models import AuditLog
from services.analysis_service import AnalysisService


@pytest.mark.django_db
class TestAnalysisServiceRunAnalysis:
    def test_creates_analysis_run_record(self, org):
        run = AnalysisService.run_analysis(org.id, "large_transaction")
        assert run is not None
        assert AnalysisRun.objects.filter(id=run.id).exists()

    def test_run_status_is_succeeded_on_success(self, org):
        run = AnalysisService.run_analysis(org.id, "large_transaction")
        assert run.status == AnalysisRun.Status.SUCCEEDED

    def test_run_stores_results_summary(self, org):
        run = AnalysisService.run_analysis(org.id, "large_transaction")
        assert run.results_summary is not None
        assert run.results_summary["analyzer"] == "large_transaction"

    def test_run_writes_audit_log(self, org):
        before_count = AuditLog.objects.filter(
            organization=org, event_type="ANALYSIS_RUN"
        ).count()
        AnalysisService.run_analysis(org.id, "large_transaction")
        after_count = AuditLog.objects.filter(
            organization=org, event_type="ANALYSIS_RUN"
        ).count()
        assert after_count == before_count + 1

    def test_run_generates_alerts_when_flagged(self, org):
        # Create small baseline txs so mean is low, then one large tx above threshold
        for i in range(5):
            Transaction.objects.create(
                organization=org,
                date=date(2026, 1, i + 1),
                vendor="Normal",
                amount=Decimal("100.00"),
            )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="HugeSpend",
            amount=Decimal("50000.00"),
        )
        before_count = Alert.objects.filter(organization=org).count()
        AnalysisService.run_analysis(org.id, "large_transaction")
        after_count = Alert.objects.filter(organization=org).count()
        assert after_count > before_count

    def test_run_no_alerts_when_nothing_flagged(self, org):
        # No transactions → nothing flagged → no alerts
        before_count = Alert.objects.filter(organization=org).count()
        AnalysisService.run_analysis(org.id, "large_transaction")
        after_count = Alert.objects.filter(organization=org).count()
        assert after_count == before_count

    def test_invalid_analysis_type_raises_value_error(self, org):
        with pytest.raises(ValueError):
            AnalysisService.run_analysis(org.id, "unknown_type")

    def test_invalid_type_does_not_create_run_record(self, org):
        before_count = AnalysisRun.objects.filter(organization=org).count()
        with pytest.raises(ValueError):
            AnalysisService.run_analysis(org.id, "unknown_type")
        after_count = AnalysisRun.objects.filter(organization=org).count()
        assert after_count == before_count

    def test_run_organisation_id_matches(self, org):
        run = AnalysisService.run_analysis(org.id, "large_transaction")
        assert str(run.organization_id) == str(org.id)

    def test_run_all_analyzer_types(self, org, transactions):
        for analyzer_type in ["large_transaction", "burn_rate", "vendor_spike", "duplicate"]:
            run = AnalysisService.run_analysis(org.id, analyzer_type)
            assert run.status == AnalysisRun.Status.SUCCEEDED
