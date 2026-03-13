import pytest
from decimal import Decimal
from datetime import date

from apps.transactions.models import Transaction
from services.analyzers.large_transaction import LargeTransactionAnalyzer
from services.analyzers.burn_rate import BurnRateAnalyzer
from services.analyzers.vendor_spike import VendorSpikeAnalyzer
from services.analyzers.duplicate import DuplicateTransactionAnalyzer
from factories.analyzer_factory import AnalyzerFactory


@pytest.mark.django_db
class TestLargeTransactionAnalyzer:
    def test_flags_transaction_above_hard_floor(self, org):
        # 5 normal transactions averaging $100; threshold = max(200, 10000) = 10000
        for i in range(5):
            Transaction.objects.create(
                organization=org,
                date=date(2026, 1, i + 1),
                vendor="Normal",
                amount=Decimal("100.00"),
            )
        big = Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="BigSpend",
            amount=Decimal("15000.00"),
        )

        result = LargeTransactionAnalyzer().run(org.id)

        assert result["analyzer"] == "large_transaction"
        assert result["flagged_count"] == 1
        flagged_ids = [str(tx["id"]) for tx in result["flagged_transactions"]]
        assert str(big.id) in flagged_ids

    def test_does_not_flag_normal_transactions(self, org):
        for i in range(5):
            Transaction.objects.create(
                organization=org,
                date=date(2026, 1, i + 1),
                vendor="Normal",
                amount=Decimal("500.00"),
            )

        result = LargeTransactionAnalyzer().run(org.id)
        # threshold = max(1000, 10000) = 10000; no transaction above that
        assert result["flagged_count"] == 0

    def test_flags_relative_outlier_above_threshold(self, org):
        # Mean $6000; threshold = max(12000, 10000) = 12000
        for i in range(5):
            Transaction.objects.create(
                organization=org,
                date=date(2026, 1, i + 1),
                vendor="Regular",
                amount=Decimal("6000.00"),
            )
        big = Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="Spike",
            amount=Decimal("13000.00"),
        )

        result = LargeTransactionAnalyzer().run(org.id)
        assert result["flagged_count"] == 1
        assert str(big.id) in [str(tx["id"]) for tx in result["flagged_transactions"]]

    def test_returns_correct_keys(self, org):
        result = LargeTransactionAnalyzer().run(org.id)
        assert "analyzer" in result
        assert "threshold" in result
        assert "flagged_count" in result
        assert "flagged_transactions" in result


@pytest.mark.django_db
class TestDuplicateTransactionAnalyzer:
    def test_detects_duplicate_same_vendor_amount_within_window(self, org):
        # Two transactions created in the same bulk_create → created_at within seconds
        tx1, tx2 = Transaction.objects.bulk_create([
            Transaction(
                organization=org,
                date=date(2026, 1, 5),
                vendor="Stripe",
                amount=Decimal("250.00"),
            ),
            Transaction(
                organization=org,
                date=date(2026, 1, 5),
                vendor="Stripe",
                amount=Decimal("250.00"),
            ),
        ])

        result = DuplicateTransactionAnalyzer().run(org.id)

        assert result["analyzer"] == "duplicate"
        assert result["duplicate_group_count"] == 1
        group = result["duplicate_groups"][0]
        assert group["vendor"] == "Stripe"
        assert group["amount"] == 250.0
        ids = group["transaction_ids"]
        assert str(tx1.id) in ids
        assert str(tx2.id) in ids

    def test_no_duplicates_for_different_vendors(self, org):
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 5),
            vendor="Stripe",
            amount=Decimal("250.00"),
        )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 5),
            vendor="PayPal",
            amount=Decimal("250.00"),
        )

        result = DuplicateTransactionAnalyzer().run(org.id)
        assert result["duplicate_group_count"] == 0

    def test_no_duplicates_for_different_amounts(self, org):
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 5),
            vendor="Stripe",
            amount=Decimal("250.00"),
        )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 5),
            vendor="Stripe",
            amount=Decimal("300.00"),
        )

        result = DuplicateTransactionAnalyzer().run(org.id)
        assert result["duplicate_group_count"] == 0

    def test_returns_window_hours_48(self, org):
        result = DuplicateTransactionAnalyzer().run(org.id)
        assert result["window_hours"] == 48


@pytest.mark.django_db
class TestVendorSpikeAnalyzer:
    def test_flags_vendor_with_30_percent_increase(self, org):
        # Previous month: $1000, current month: $1300 (30% increase — above 25% threshold)
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 15),
            vendor="VendorA",
            amount=Decimal("1000.00"),
        )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 2, 15),
            vendor="VendorA",
            amount=Decimal("1300.00"),
        )

        result = VendorSpikeAnalyzer().run(org.id)

        assert result["analyzer"] == "vendor_spike"
        flagged_vendors = [v["vendor"] for v in result["flagged_vendors"]]
        assert "VendorA" in flagged_vendors

    def test_does_not_flag_vendor_below_threshold(self, org):
        # $1000 → $1100 (10% — below 25% threshold)
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 15),
            vendor="StableVendor",
            amount=Decimal("1000.00"),
        )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 2, 15),
            vendor="StableVendor",
            amount=Decimal("1100.00"),
        )

        result = VendorSpikeAnalyzer().run(org.id)
        flagged_vendors = [v["vendor"] for v in result["flagged_vendors"]]
        assert "StableVendor" not in flagged_vendors

    def test_flags_new_vendor_with_no_prior_baseline(self, org):
        # OldVendor only in Jan, NewVendor only in Feb → NewVendor flagged
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 15),
            vendor="OldVendor",
            amount=Decimal("500.00"),
        )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 2, 15),
            vendor="NewVendor",
            amount=Decimal("800.00"),
        )

        result = VendorSpikeAnalyzer().run(org.id)
        flagged_vendors = [v["vendor"] for v in result["flagged_vendors"]]
        assert "NewVendor" in flagged_vendors

    def test_insufficient_data_returns_note(self, org):
        # Only one month of data → can't compare, returns note
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 15),
            vendor="VendorX",
            amount=Decimal("500.00"),
        )

        result = VendorSpikeAnalyzer().run(org.id)
        assert "note" in result
        assert result["flagged_vendors"] == []


@pytest.mark.django_db
class TestBurnRateAnalyzer:
    def test_returns_positive_burn_and_runway(self, org):
        # Expenses > Revenue → positive burn, runway computed
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="Landlord",
            amount=Decimal("5000.00"),
            category="Overhead",
        )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 15),
            vendor="Customer",
            amount=Decimal("1000.00"),
            category="Revenue",  # must match REVENUE_CATEGORY = "Revenue"
        )

        result = BurnRateAnalyzer().run(org.id)

        assert result["analyzer"] == "burn_rate"
        assert result["net_monthly_burn"] > 0
        assert result["runway_months"] is not None

    def test_runway_is_none_when_cash_flow_positive(self, org):
        # Revenue > Expenses → no burn → runway = None
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 10),
            vendor="BigClient",
            amount=Decimal("10000.00"),
            category="Revenue",
        )
        Transaction.objects.create(
            organization=org,
            date=date(2026, 1, 15),
            vendor="Office",
            amount=Decimal("500.00"),
            category="Overhead",
        )

        result = BurnRateAnalyzer().run(org.id)

        assert result["net_monthly_burn"] <= 0
        assert result["runway_months"] is None

    def test_returns_correct_keys(self, org):
        result = BurnRateAnalyzer().run(org.id)
        assert "analyzer" in result
        assert "avg_monthly_expenses" in result
        assert "avg_monthly_revenue" in result
        assert "net_monthly_burn" in result
        assert "runway_months" in result


class TestAnalyzerFactory:
    def test_create_known_types(self):
        for key in ["large_transaction", "burn_rate", "vendor_spike", "duplicate"]:
            analyzer = AnalyzerFactory.create(key)
            assert analyzer is not None

    def test_create_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown analyzer type"):
            AnalyzerFactory.create("nonexistent_analyzer")

    def test_available_returns_list_of_known_types(self):
        available = AnalyzerFactory.available()
        assert isinstance(available, list)
        assert "large_transaction" in available
        assert "burn_rate" in available
        assert "vendor_spike" in available
        assert "duplicate" in available
