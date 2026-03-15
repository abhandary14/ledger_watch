import pytest
import uuid

from apps.alerts.models import Alert
from apps.audit.models import AuditLog
from services.alert_service import AlertService


@pytest.mark.django_db
class TestAlertServiceLargeTransaction:
    def _make_results(self, threshold, transactions):
        return {
            "analyzer": "large_transaction",
            "threshold": threshold,
            "flagged_count": len(transactions),
            "flagged_transactions": transactions,
        }

    def test_creates_alert_for_each_flagged_transaction(self, org):
        tx_id = str(uuid.uuid4())
        results = self._make_results(10000.0, [
            {"id": tx_id, "vendor": "BigCo", "amount": 15000.0, "date": "2026-01-10"},
        ])
        alerts = AlertService.generate_alerts(org.id, "large_transaction", results)
        assert len(alerts) == 1
        assert Alert.objects.filter(id=alerts[0].id).exists()

    def test_medium_severity_for_amount_below_2_5x_threshold(self, org):
        # amount = 1.5 * threshold → NOT > 2.5 * threshold → MEDIUM
        threshold = 10000.0
        amount = threshold * 1.5
        tx_id = str(uuid.uuid4())
        results = self._make_results(threshold, [
            {"id": tx_id, "vendor": "MidCo", "amount": amount, "date": "2026-01-10"},
        ])
        alerts = AlertService.generate_alerts(org.id, "large_transaction", results)
        assert alerts[0].severity == Alert.Severity.MEDIUM

    def test_high_severity_for_amount_above_2_5x_threshold(self, org):
        # amount > 2.5 * threshold → HIGH (equivalent to > 5x mean)
        threshold = 10000.0
        amount = threshold * 3.0
        tx_id = str(uuid.uuid4())
        results = self._make_results(threshold, [
            {"id": tx_id, "vendor": "HugeCo", "amount": amount, "date": "2026-01-10"},
        ])
        alerts = AlertService.generate_alerts(org.id, "large_transaction", results)
        assert alerts[0].severity == Alert.Severity.HIGH

    def test_no_alerts_for_empty_flagged_list(self, org):
        results = self._make_results(10000.0, [])
        alerts = AlertService.generate_alerts(org.id, "large_transaction", results)
        assert len(alerts) == 0


@pytest.mark.django_db
class TestAlertServiceBurnRate:
    def test_high_severity_for_runway_below_3_months(self, org):
        results = {
            "analyzer": "burn_rate",
            "avg_monthly_expenses": 10000.0,
            "avg_monthly_revenue": 1000.0,
            "net_monthly_burn": 9000.0,
            "runway_months": 1.5,
        }
        alerts = AlertService.generate_alerts(org.id, "burn_rate", results)
        assert len(alerts) == 1
        assert alerts[0].severity == Alert.Severity.HIGH

    def test_medium_severity_for_runway_3_to_6_months(self, org):
        results = {
            "analyzer": "burn_rate",
            "avg_monthly_expenses": 5000.0,
            "avg_monthly_revenue": 2000.0,
            "net_monthly_burn": 3000.0,
            "runway_months": 4.0,
        }
        alerts = AlertService.generate_alerts(org.id, "burn_rate", results)
        assert len(alerts) == 1
        assert alerts[0].severity == Alert.Severity.MEDIUM

    def test_low_severity_for_runway_above_6_months(self, org):
        results = {
            "analyzer": "burn_rate",
            "avg_monthly_expenses": 2000.0,
            "avg_monthly_revenue": 1000.0,
            "net_monthly_burn": 1000.0,
            "runway_months": 8.0,
        }
        alerts = AlertService.generate_alerts(org.id, "burn_rate", results)
        assert len(alerts) == 1
        assert alerts[0].severity == Alert.Severity.LOW

    def test_no_alert_when_cash_flow_positive(self, org):
        results = {
            "analyzer": "burn_rate",
            "avg_monthly_expenses": 1000.0,
            "avg_monthly_revenue": 5000.0,
            "net_monthly_burn": -4000.0,
            "runway_months": None,
        }
        alerts = AlertService.generate_alerts(org.id, "burn_rate", results)
        assert len(alerts) == 0


@pytest.mark.django_db
class TestAlertServiceDuplicate:
    def test_low_severity_for_duplicate_group(self, org):
        tx_id1 = str(uuid.uuid4())
        tx_id2 = str(uuid.uuid4())
        results = {
            "analyzer": "duplicate",
            "window_hours": 48,
            "duplicate_group_count": 1,
            "duplicate_groups": [
                {
                    "vendor": "Stripe",
                    "amount": 250.0,
                    "transaction_ids": [tx_id1, tx_id2],
                    "dates": ["2026-01-05", "2026-01-05"],
                }
            ],
        }
        alerts = AlertService.generate_alerts(org.id, "duplicate", results)
        assert len(alerts) == 1
        assert alerts[0].severity == Alert.Severity.LOW
        assert alerts[0].alert_type == "duplicate"

    def test_no_alerts_for_no_duplicates(self, org):
        results = {
            "analyzer": "duplicate",
            "window_hours": 48,
            "duplicate_group_count": 0,
            "duplicate_groups": [],
        }
        alerts = AlertService.generate_alerts(org.id, "duplicate", results)
        assert len(alerts) == 0


@pytest.mark.django_db
class TestAlertServiceVendorSpike:
    def test_low_severity_for_25_to_50_percent_increase(self, org):
        results = {
            "analyzer": "vendor_spike",
            "spike_threshold_pct": 25.0,
            "current_month": "2026-02-01",
            "previous_month": "2026-01-01",
            "flagged_count": 1,
            "flagged_vendors": [
                {
                    "vendor": "VendorA",
                    "previous_month_spend": 1000.0,
                    "current_month_spend": 1300.0,
                    "increase_pct": 30.0,
                }
            ],
        }
        alerts = AlertService.generate_alerts(org.id, "vendor_spike", results)
        assert len(alerts) == 1
        assert alerts[0].severity == Alert.Severity.LOW

    def test_medium_severity_for_50_percent_or_more_increase(self, org):
        results = {
            "analyzer": "vendor_spike",
            "spike_threshold_pct": 25.0,
            "current_month": "2026-02-01",
            "previous_month": "2026-01-01",
            "flagged_count": 1,
            "flagged_vendors": [
                {
                    "vendor": "VendorB",
                    "previous_month_spend": 1000.0,
                    "current_month_spend": 1600.0,
                    "increase_pct": 60.0,
                }
            ],
        }
        alerts = AlertService.generate_alerts(org.id, "vendor_spike", results)
        assert len(alerts) == 1
        assert alerts[0].severity == Alert.Severity.MEDIUM

    def test_low_severity_for_new_vendor(self, org):
        results = {
            "analyzer": "vendor_spike",
            "spike_threshold_pct": 25.0,
            "current_month": "2026-02-01",
            "previous_month": "2026-01-01",
            "flagged_count": 1,
            "flagged_vendors": [
                {
                    "vendor": "NewVendorX",
                    "previous_month_spend": 0.0,
                    "current_month_spend": 800.0,
                    "increase_pct": None,
                }
            ],
        }
        alerts = AlertService.generate_alerts(org.id, "vendor_spike", results)
        assert len(alerts) == 1
        assert alerts[0].severity == Alert.Severity.LOW

    def test_writes_audit_log_for_alerts(self, org):
        results = {
            "analyzer": "vendor_spike",
            "spike_threshold_pct": 25.0,
            "current_month": "2026-02-01",
            "previous_month": "2026-01-01",
            "flagged_count": 1,
            "flagged_vendors": [
                {
                    "vendor": "SpikeVendor",
                    "previous_month_spend": 1000.0,
                    "current_month_spend": 2000.0,
                    "increase_pct": 100.0,
                }
            ],
        }
        before = AuditLog.objects.filter(
            organization=org, event_type="ALERTS_GENERATED"
        ).count()
        AlertService.generate_alerts(org.id, "vendor_spike", results)
        after = AuditLog.objects.filter(
            organization=org, event_type="ALERTS_GENERATED"
        ).count()
        assert after == before + 1

    def test_unknown_analyzer_returns_empty_list(self, org):
        results = {"analyzer": "unknown", "data": []}
        alerts = AlertService.generate_alerts(org.id, "unknown", results)
        assert alerts == []
