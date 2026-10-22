"""
seed_transactions — Django management command to populate synthetic transaction data.

Generates realistic-looking but entirely fake financial data for development and
testing purposes. No real financial data is used.

Seeds exactly --count transactions over the 12 months ending today. A fixed set of
FIXED_COUNT anomalies (large charges, vendor spikes, duplicate pairs) is always
included so every analyzer has something to flag; the rest of --count is split
between recurring vendor charges and customer revenue.

Usage:
    python manage.py seed_transactions
    python manage.py seed_transactions --count 100
    python manage.py seed_transactions --org "My Org" --clear
"""

import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction
from django_tenants.utils import tenant_context

from apps.organizations.models import Domain, Organization
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

DEFAULT_COUNT = 265
NUM_MONTHS = 12

# Fixed anomaly sets — always seeded, whatever --count is, so every analyzer fires.
LARGE_TX_COUNT = 10  # LargeTransactionAnalyzer
SPIKE_VENDORS = [("Cloudflare", "infrastructure"), ("PagerDuty", "developer_tools")]  # VendorSpikeAnalyzer
DUPLICATE_VENDORS = ["Stripe", "AWS", "Twilio", "GitHub", "Datadog"]  # DuplicateTransactionAnalyzer, one pair each
FIXED_COUNT = LARGE_TX_COUNT + len(SPIKE_VENDORS) + 2 * len(DUPLICATE_VENDORS)

# Share of the scalable (non-anomaly) transactions that are customer revenue.
REVENUE_SHARE = 0.14

# Extra spend added to each spike vendor's current month, relative to that
# month's normal spend — well above VendorSpikeAnalyzer's 25% threshold.
SPIKE_RATIO = 0.60


def _recurring_counts(total: int, num_months: int, num_vendors: int) -> list[list[int]]:
    """
    Spread *total* recurring charges over a months × vendors grid.

    Every slot gets the same base count. The remainder is handed out one vendor
    at a time across all of its months (oldest first), so a vendor never has more
    charges in the current month than in the previous one — VendorSpikeAnalyzer
    then only flags the deliberate spikes.
    """
    base, extra = divmod(total, num_months * num_vendors)
    counts = [[base] * num_vendors for _ in range(num_months)]
    for i in range(extra):
        vendor_idx, month_idx = divmod(i, num_months)
        counts[month_idx][vendor_idx] += 1
    return counts


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
            default=DEFAULT_COUNT,
            help=(
                f"Exact number of transactions to generate (default: {DEFAULT_COUNT}, "
                f"minimum: {FIXED_COUNT} — the fixed anomaly set every analyzer needs)."
            ),
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
            "--clear-only",
            action="store_true",
            default=False,
            help="Delete all existing transactions for the target org and exit without seeding.",
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
        do_clear: bool = options["clear"] or options["clear_only"]

        # Validate before touching the database (or creating an org).
        if not options["clear_only"] and options["count"] < FIXED_COUNT:
            raise CommandError(
                f"--count must be at least {FIXED_COUNT} "
                "(the fixed anomaly set every analyzer needs)."
            )

        # ------------------------------------------------------------------
        # 1. Ensure organization exists
        # ------------------------------------------------------------------
        org = Organization.objects.filter(name=org_name).first()
        if org is None:
            # Mirror RegisterView: a tenant needs a schema_name and a Domain row.
            with db_transaction.atomic():
                org = Organization(name=org_name, schema_name=f"tenant_{uuid.uuid4().hex[:12]}")
                org.save()  # auto_create_schema=True creates the PG schema + runs tenant migrations
                Domain.objects.create(
                    domain=f"{org.id}.ledgerwatch.local",
                    tenant=org,
                    is_primary=True,
                )
            self.stdout.write(self.style.SUCCESS(f"Created organization: '{org_name}'"))
        else:
            self.stdout.write(f"Using existing organization: '{org_name}'")

        # Transactions live in the org's own schema.
        with tenant_context(org):
            self._seed(org_name, do_clear, options, fake, rng)

    def _seed(self, org_name, do_clear, options, fake, rng):
        # ------------------------------------------------------------------
        # 2. Optionally clear existing transactions
        # ------------------------------------------------------------------
        if do_clear:
            deleted_count, _ = Transaction.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Cleared {deleted_count} existing transactions.")
            )

        if options["clear_only"]:
            return

        # ------------------------------------------------------------------
        # 3. Determine date window — 12 months ending today
        # ------------------------------------------------------------------
        today = date.today()
        # month_starts[0] = 11 months ago (oldest), month_starts[-1] = current month
        month_starts = [_month_start(today, offset) for offset in range(NUM_MONTHS - 1, -1, -1)]

        # Everything beyond the fixed anomaly sets scales with --count.
        scalable = options["count"] - FIXED_COUNT
        revenue_count = round(scalable * REVENUE_SHARE)
        recurring_count = scalable - revenue_count

        # ------------------------------------------------------------------
        # 4. Build transaction list
        # ------------------------------------------------------------------
        transactions: list[Transaction] = []

        # --- 4a. Recurring vendor transactions (spread evenly over months × vendors) ---
        # Each vendor has a stable baseline amount with ±10% noise per charge.
        baseline_amounts: dict[str, float] = {}
        for vendor, _ in RECURRING_VENDORS:
            baseline_amounts[vendor] = round(rng.uniform(200.0, 2000.0), 2)

        recurring_counts = _recurring_counts(recurring_count, len(month_starts), len(RECURRING_VENDORS))
        for month_idx, month_start in enumerate(month_starts):
            for vendor_idx, (vendor, category) in enumerate(RECURRING_VENDORS):
                for _ in range(recurring_counts[month_idx][vendor_idx]):
                    noise = rng.uniform(0.90, 1.10)
                    amount = Decimal(str(round(baseline_amounts[vendor] * noise, 2)))
                    tx_date = _random_date_in_month(month_start, rng, max_date=today)
                    transactions.append(
                        Transaction(
                            date=tx_date,
                            vendor=vendor,
                            amount=amount,
                            description=fake.bs(),
                            category=category,
                        )
                    )

        # --- 4b. Customer revenue transactions (REVENUE_SHARE of the scalable count) ---
        for _ in range(revenue_count):
            month_start = rng.choice(month_starts)
            amount = Decimal(str(round(rng.uniform(500.0, 5000.0), 2)))
            tx_date = _random_date_in_month(month_start, rng, max_date=today)
            transactions.append(
                Transaction(
                    date=tx_date,
                    vendor=REVENUE_VENDOR,
                    amount=amount,
                    description=fake.catch_phrase(),
                    category="Revenue",
                )
            )

        # --- 4c. Anomalous large transactions to trigger LargeTransactionAnalyzer ---
        # Threshold = max(2 * mean, 10000). With mean ~$500-$1000, threshold ~$10,000.
        # Amounts well above $15,000 ensure reliable triggering.
        large_vendors = [v for v, _ in RECURRING_VENDORS[:5]]
        for i in range(LARGE_TX_COUNT):
            vendor = large_vendors[i % len(large_vendors)]
            amount = Decimal(str(round(rng.uniform(15000.0, 50000.0), 2)))
            month_start = rng.choice(month_starts)
            tx_date = _random_date_in_month(month_start, rng, max_date=today)
            transactions.append(
                Transaction(
                    date=tx_date,
                    vendor=vendor,
                    amount=amount,
                    description=f"Anomalous charge: {fake.bs()}",
                    category="infrastructure",
                )
            )

        # --- 4d. Vendor spikes in most recent month for VendorSpikeAnalyzer ---
        # One extra charge worth SPIKE_RATIO of the vendor's normal monthly spend, so
        # the month-over-month increase stays above 25% however many recurring
        # charges --count produced. With no recurring charges the vendor shows up as
        # new in the current month, which is flagged too.
        current_month_start = month_starts[-1]
        vendor_index = {vendor: idx for idx, (vendor, _) in enumerate(RECURRING_VENDORS)}
        for vendor, category in SPIKE_VENDORS:
            charges_this_month = max(1, recurring_counts[-1][vendor_index[vendor]])
            spike_amount = Decimal(str(round(baseline_amounts[vendor] * charges_this_month * SPIKE_RATIO, 2)))
            tx_date = _random_date_in_month(current_month_start, rng, max_date=today)
            transactions.append(
                Transaction(
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

        # --- 4e. Near-duplicate transaction pairs for DuplicateTransactionAnalyzer ---
        # Inserted in a separate bulk_create so both records in each pair share
        # a tightly grouped created_at timestamp (within the same DB round-trip).
        vendor_category = dict(RECURRING_VENDORS)
        duplicate_transactions: list[Transaction] = []
        for vendor in DUPLICATE_VENDORS:
            amount = Decimal(str(round(rng.uniform(100.0, 1500.0), 2)))
            tx_date = _random_date_in_month(current_month_start, rng, max_date=today)
            category = vendor_category.get(vendor, "developer_tools")
            for _ in range(2):  # exact duplicate pair
                duplicate_transactions.append(
                    Transaction(
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
