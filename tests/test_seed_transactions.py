from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.transactions.management.commands.seed_transactions import (
    DEFAULT_COUNT,
    DUPLICATE_VENDORS,
    FIXED_COUNT,
    NUM_MONTHS,
    RECURRING_VENDORS,
    SPIKE_VENDORS,
    _recurring_counts,
)
from apps.transactions.models import Transaction
from services.analyzers.duplicate import DuplicateTransactionAnalyzer
from services.analyzers.large_transaction import LargeTransactionAnalyzer
from services.analyzers.vendor_spike import VendorSpikeAnalyzer


def seed(org, *args):
    """Run seed_transactions into *org*'s schema (the `org` fixture is already active)."""
    call_command("seed_transactions", "--org", org.name, *args, stdout=StringIO())


class TestRecurringCounts:
    @pytest.mark.parametrize("total", [0, 1, 11, 119, 120, 121, 209, 1000])
    def test_sums_to_total(self, total):
        counts = _recurring_counts(total, NUM_MONTHS, len(RECURRING_VENDORS))
        assert sum(map(sum, counts)) == total

    @pytest.mark.parametrize("total", [0, 1, 11, 119, 120, 121, 209, 1000])
    def test_spread_is_even(self, total):
        counts = _recurring_counts(total, NUM_MONTHS, len(RECURRING_VENDORS))
        flat = [c for month in counts for c in month]
        assert max(flat) - min(flat) <= 1

    @pytest.mark.parametrize("total", [0, 1, 11, 119, 120, 121, 209, 1000])
    def test_current_month_never_exceeds_previous(self, total):
        # Otherwise VendorSpikeAnalyzer would flag ordinary vendors.
        counts = _recurring_counts(total, NUM_MONTHS, len(RECURRING_VENDORS))
        for vendor_idx in range(len(RECURRING_VENDORS)):
            assert counts[-1][vendor_idx] <= counts[-2][vendor_idx]


@pytest.mark.django_db
class TestSeedCount:
    def test_default_count(self, org):
        seed(org, "--seed", "1")
        assert Transaction.objects.count() == DEFAULT_COUNT

    @pytest.mark.parametrize("count", [FIXED_COUNT, 50, 100, 1000])
    def test_seeds_exactly_count(self, org, count):
        seed(org, "--count", str(count), "--seed", "1")
        assert Transaction.objects.count() == count

    def test_below_minimum_raises_and_seeds_nothing(self, org):
        with pytest.raises(CommandError, match=str(FIXED_COUNT)):
            seed(org, "--count", str(FIXED_COUNT - 1))
        assert Transaction.objects.count() == 0

    def test_clear_replaces_existing_transactions(self, org):
        seed(org, "--count", "100", "--seed", "1")
        seed(org, "--count", "60", "--seed", "2", "--clear")
        assert Transaction.objects.count() == 60

    def test_clear_only_ignores_count(self, org):
        seed(org, "--count", "100", "--seed", "1")
        seed(org, "--count", "0", "--clear-only")
        assert Transaction.objects.count() == 0


@pytest.mark.django_db
class TestSeededDataTriggersAnalyzers:
    @pytest.mark.parametrize("seed_value", ["1", "2", "3"])
    @pytest.mark.parametrize("count", [FIXED_COUNT, 100, DEFAULT_COUNT, 1000])
    def test_every_anomaly_analyzer_flags(self, org, count, seed_value):
        seed(org, "--count", str(count), "--seed", seed_value)

        assert LargeTransactionAnalyzer().run()["flagged_count"] >= 1

        duplicates = DuplicateTransactionAnalyzer().run()
        assert duplicates["duplicate_group_count"] >= len(DUPLICATE_VENDORS)

        flagged = {v["vendor"] for v in VendorSpikeAnalyzer().run()["flagged_vendors"]}
        for vendor, _ in SPIKE_VENDORS:
            assert vendor in flagged
