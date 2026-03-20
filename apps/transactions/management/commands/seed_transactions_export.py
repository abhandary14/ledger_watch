"""
seed_transactions_export — generate synthetic transactions and write them to a CSV file.

Produces the same realistic-looking fake data as seed_transactions but writes
it to a CSV file instead of (or as well as) the database.  The CSV columns match
the format expected by the transaction import wizard:
    date, vendor, amount, category, description

Usage:
    python manage.py seed_transactions_export
    python manage.py seed_transactions_export --count 100 --output transactions.csv
    python manage.py seed_transactions_export --seed 42 --output /tmp/seed.csv
"""

import csv
import random
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.transactions.management.commands.seed_transactions import (
    RECURRING_VENDORS,
    REVENUE_VENDOR,
    _month_start,
    _random_date_in_month,
)

try:
    from faker import Faker
except ImportError as exc:
    raise ImportError(
        "The 'faker' package is required for seed_transactions_export. "
        "Install it with: pip install faker"
    ) from exc

_CSV_FIELDS = ["date", "vendor", "amount", "category", "description"]


class Command(BaseCommand):
    help = (
        "Generate synthetic transaction data and export it to a CSV file. "
        "The CSV format matches the transaction import wizard."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=265,
            help="Approximate number of transactions to generate (default: 265).",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="seed_transactions.csv",
            metavar="FILE",
            help="Path for the output CSV file (default: seed_transactions.csv).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Integer random seed for reproducible output (omit for random).",
        )

    def handle(self, *args, **options):
        fake = Faker()
        rng = random.Random(options["seed"])
        output_path = Path(options["output"])

        today = date.today()
        month_starts = [_month_start(today, offset) for offset in range(5, -1, -1)]
        current_month_start = month_starts[-1]

        rows: list[dict] = []

        # recurring vendor transactions
        baseline_amounts: dict[str, float] = {}
        for vendor, _ in RECURRING_VENDORS:
            baseline_amounts[vendor] = round(rng.uniform(200.0, 2000.0), 2)

        for month_idx, month_start in enumerate(month_starts):
            for vendor, category in RECURRING_VENDORS:
                num_txs = 2 if month_idx < 5 else 3
                for _ in range(num_txs):
                    noise = rng.uniform(0.90, 1.10)
                    amount = Decimal(str(round(baseline_amounts[vendor] * noise, 2)))
                    rows.append({
                        "date": _random_date_in_month(month_start, rng, max_date=today).isoformat(),
                        "vendor": vendor,
                        "amount": str(amount),
                        "category": category,
                        "description": fake.bs(),
                    })

        # revenue transactions
        for _ in range(50):
            month_start = rng.choice(month_starts)
            amount = Decimal(str(round(rng.uniform(500.0, 5000.0), 2)))
            rows.append({
                "date": _random_date_in_month(month_start, rng, max_date=today).isoformat(),
                "vendor": REVENUE_VENDOR,
                "amount": str(amount),
                "category": "Revenue",
                "description": fake.catch_phrase(),
            })

        # large, anomalous transactions
        large_vendors = [v for v, _ in RECURRING_VENDORS[:5]]
        for i in range(10):
            vendor = large_vendors[i % len(large_vendors)]
            amount = Decimal(str(round(rng.uniform(15000.0, 50000.0), 2)))
            month_start = rng.choice(month_starts)
            rows.append({
                "date": _random_date_in_month(month_start, rng, max_date=today).isoformat(),
                "vendor": vendor,
                "amount": str(amount),
                "category": "infrastructure",
                "description": f"Anomalous charge: {fake.bs()}",
            })

        # vendor spike transactions
        spike_vendors = [("Cloudflare", "infrastructure"), ("PagerDuty", "developer_tools")]
        for vendor, category in spike_vendors:
            spike_amount = Decimal(str(round(baseline_amounts[vendor] * 0.60, 2)))
            rows.append({
                "date": _random_date_in_month(current_month_start, rng, max_date=today).isoformat(),
                "vendor": vendor,
                "amount": str(spike_amount),
                "category": category,
                "description": f"Spike charge: {fake.bs()}",
            })

        # near-duplicate pairs
        dup_vendors = ["Stripe", "AWS", "Twilio", "GitHub", "Datadog"]
        vendor_category = dict(RECURRING_VENDORS)
        for vendor in dup_vendors:
            amount = Decimal(str(round(rng.uniform(100.0, 1500.0), 2)))
            tx_date = _random_date_in_month(current_month_start, rng, max_date=today).isoformat()
            category = vendor_category.get(vendor, "developer_tools")
            for _ in range(2):
                rows.append({
                    "date": tx_date,
                    "vendor": vendor,
                    "amount": str(amount),
                    "category": category,
                    "description": "Duplicate charge — pending investigation",
                })

        # export csv
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {len(rows)} transactions to '{output_path}'."
            )
        )
