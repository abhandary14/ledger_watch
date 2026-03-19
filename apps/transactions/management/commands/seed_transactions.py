"""
seed_transactions — Django management command to populate synthetic transaction data.

Generates realistic-looking but entirely fake financial data for development and
testing purposes. No real financial data is used.

Usage:
    python manage.py seed_transactions
    python manage.py seed_transactions --count 265
    python manage.py seed_transactions --org "My Org" --clear
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.organizations.models import Organization
from apps.transactions.models import Transaction

try:
    from faker import Faker
except ImportError as exc:
    raise ImportError(
        "The 'faker' package is required for seed_transactions. "
        "Install it with: pip install faker"
    ) from exc


# ---------------------------------------------------------------------------
# Vendor catalogue — entirely synthetic names / categories
# ---------------------------------------------------------------------------

RECURRING_VENDORS = [
    ("AWS", "infrastructure"),
    ("Stripe", "payment_processing"),
    ("Twilio", "communications"),
    ("GitHub", "developer_tools"),
    ("Datadog", "developer_tools"),
    ("Cloudflare", "infrastructure"),
    ("Slack", "communications"),
    ("SendGrid", "communications"),
    ("PagerDuty", "developer_tools"),
    ("Snowflake", "infrastructure"),
]

REVENUE_VENDOR = "Customer Payment"


def _month_start(reference: date, months_back: int) -> date:
    """Return the first day of the month `months_back` months before `reference`."""
    year = reference.year
    month = reference.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def _month_end(month_start: date) -> date:
    """Return the last day of the month given its first day."""
    year = month_start.year
    month = month_start.month + 1
    if month > 12:
        month = 1
        year += 1
    return date(year, month, 1) - timedelta(days=1)


def _random_date_in_month(month_start: date, rng: random.Random, max_date: date | None = None) -> date:
    end = _month_end(month_start)
    if max_date is not None and max_date < end:
        end = max(max_date, month_start)
    delta = (end - month_start).days
    return month_start + timedelta(days=rng.randint(0, delta))


class Command(BaseCommand):
    help = (
        "Seed the database with synthetic transaction data for development/testing. "
        "No real financial data is used."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=265,
            help="Approximate total number of transactions to generate (default: 265).",
        )
        parser.add_argument(
            "--org",
            type=str,
            default="Acme Corp",
            help="Name of the organization to seed data for (default: 'Acme Corp').",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            default=False,
            help="Delete all existing transactions for the target org before seeding.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Integer random seed for reproducible data generation (omit for random output).",
        )

    def handle(self, *args, **options):
        fake = Faker()
        rng = random.Random(options["seed"])

        org_name: str = options["org"]
        do_clear: bool = options["clear"]

        # ------------------------------------------------------------------
        # 1. Ensure organization exists
        # ------------------------------------------------------------------
        org, created = Organization.objects.get_or_create(name=org_name)
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created organization: '{org_name}'"))
        else:
            self.stdout.write(f"Using existing organization: '{org_name}'")

        # ------------------------------------------------------------------
        # 2. Optionally clear existing transactions
        # ------------------------------------------------------------------
        if do_clear:
            deleted_count, _ = Transaction.objects.filter(organization=org).delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared {deleted_count} existing transactions.")
            )

        # ------------------------------------------------------------------
        # 3. Determine date window — 6 months ending today
        # ------------------------------------------------------------------
        today = date.today()
        # month_starts[0] = 5 months ago (oldest), month_starts[5] = current month
        month_starts = [_month_start(today, offset) for offset in range(5, -1, -1)]

        # ------------------------------------------------------------------
        # 4. Build transaction list
        # ------------------------------------------------------------------
        transactions: list[Transaction] = []

        # --- 4a. Recurring vendor transactions (200 total, ~33/month) ---
        # Stable baseline per vendor for months 0-4, then spike in month 5.
        baseline_amounts: dict[str, float] = {}
        for vendor, _ in RECURRING_VENDORS:
            baseline_amounts[vendor] = round(rng.uniform(200.0, 2000.0), 2)

        for month_idx, month_start in enumerate(month_starts):
            for vendor, category in RECURRING_VENDORS:
                # 2 transactions per vendor per month for first 5 months, 3 in current
                num_txs = 2 if month_idx < 5 else 3
                for _ in range(num_txs):
                    noise = rng.uniform(0.90, 1.10)
                    amount = Decimal(str(round(baseline_amounts[vendor] * noise, 2)))
                    tx_date = _random_date_in_month(month_start, rng, max_date=today)
                    transactions.append(
                        Transaction(
                            organization=org,
                            date=tx_date,
                            vendor=vendor,
                            amount=amount,
                            description=fake.bs(),
                            category=category,
                        )
                    )

        # --- 4b. Customer revenue transactions (50 total) ---
        for _ in range(50):
            month_start = rng.choice(month_starts)
            amount = Decimal(str(round(rng.uniform(500.0, 5000.0), 2)))
            tx_date = _random_date_in_month(month_start, rng, max_date=today)
            transactions.append(
                Transaction(
                    organization=org,
                    date=tx_date,
                    vendor=REVENUE_VENDOR,
                    amount=amount,
                    description=fake.catch_phrase(),
                    category="revenue",
                )
            )

        # --- 4c. Anomalous large transactions (10) to trigger LargeTransactionAnalyzer ---
        # Threshold = max(2 * mean, 10000). With mean ~$500-$1000, threshold ~$10,000.
        # Amounts well above $15,000 ensure reliable triggering.
        large_vendors = [v for v, _ in RECURRING_VENDORS[:5]]
        for i in range(10):
            vendor = large_vendors[i % len(large_vendors)]
            amount = Decimal(str(round(rng.uniform(15000.0, 50000.0), 2)))
            month_start = rng.choice(month_starts)
            tx_date = _random_date_in_month(month_start, rng, max_date=today)
            transactions.append(
                Transaction(
                    organization=org,
                    date=tx_date,
                    vendor=vendor,
                    amount=amount,
                    description=f"Anomalous charge: {fake.bs()}",
                    category="infrastructure",
                )
            )

        # --- 4d. Vendor spikes in most recent month for VendorSpikeAnalyzer ---
        # Add extra spend >= 25% above the baseline for two vendors in current month.
        spike_vendors = [("Cloudflare", "infrastructure"), ("PagerDuty", "developer_tools")]
        current_month_start = month_starts[-1]
        for vendor, category in spike_vendors:
            # Add 60% of baseline as an extra charge — safely above the 25% spike threshold
            spike_amount = Decimal(str(round(baseline_amounts[vendor] * 0.60, 2)))
            tx_date = _random_date_in_month(current_month_start, rng, max_date=today)
            transactions.append(
                Transaction(
                    organization=org,
                    date=tx_date,
                    vendor=vendor,
                    amount=spike_amount,
                    description=f"Spike charge: {fake.bs()}",
                    category=category,
                )
            )

        # Persist all non-duplicate transactions
        Transaction.objects.bulk_create(transactions)
        self.stdout.write(
            self.style.SUCCESS(f"Created {len(transactions)} synthetic transactions.")
        )

        # --- 4e. Near-duplicate transaction pairs (5 pairs) for DuplicateTransactionAnalyzer ---
        # Inserted in a separate bulk_create so both records in each pair share
        # a tightly grouped created_at timestamp (within the same DB round-trip).
        dup_vendors = ["Stripe", "AWS", "Twilio", "GitHub", "Datadog"]
        vendor_category = dict(RECURRING_VENDORS)
        duplicate_transactions: list[Transaction] = []
        for vendor in dup_vendors:
            amount = Decimal(str(round(rng.uniform(100.0, 1500.0), 2)))
            tx_date = _random_date_in_month(current_month_start, rng, max_date=today)
            category = vendor_category.get(vendor, "developer_tools")
            for _ in range(2):  # exact duplicate pair
                duplicate_transactions.append(
                    Transaction(
                        organization=org,
                        date=tx_date,
                        vendor=vendor,
                        amount=amount,
                        description="Duplicate charge — pending investigation",
                        category=category,
                    )
                )

        Transaction.objects.bulk_create(duplicate_transactions)
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(duplicate_transactions)} near-duplicate transactions "
                f"({len(duplicate_transactions) // 2} pairs)."
            )
        )

        total = len(transactions) + len(duplicate_transactions)
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Seeded {total} total transactions for org '{org_name}'."
            )
        )
