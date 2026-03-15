"""
VendorSpikeAnalyzer — detects vendors with a month-over-month spending spike.

Logic:
- Compare the most recent full calendar month's spend per vendor against the
  previous calendar month.
- Flag any vendor whose spend increased by >= SPIKE_THRESHOLD (default 25%).
- Vendors that appear only in the current month (no prior baseline) are flagged
  as new vendors with infinite growth.
"""

from uuid import UUID

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from apps.transactions.models import Transaction
from services.analyzers.base import Analyzer

SPIKE_THRESHOLD = 0.25  # 25%


class VendorSpikeAnalyzer(Analyzer):
    def run(self, organization_id: UUID | str) -> dict:
        txs = Transaction.objects.filter(organization_id=organization_id)

        monthly = (
            txs.annotate(month=TruncMonth("date"))
            .values("month", "vendor")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        # Build { vendor: { month: total } }
        spend: dict[str, dict] = {}
        months: set = set()
        for row in monthly:
            m = row["month"]
            months.add(m)
            spend.setdefault(row["vendor"], {})[m] = float(row["total"])

        if len(months) < 2:
            return {
                "analyzer": "vendor_spike",
                "spike_threshold_pct": SPIKE_THRESHOLD * 100,
                "flagged_vendors": [],
                "note": "Insufficient data — need at least two months of transactions.",
            }

        sorted_months = sorted(months)
        current_month = sorted_months[-1]
        previous_month = sorted_months[-2]

        flagged = []
        for vendor, by_month in spend.items():
            current = by_month.get(current_month, 0.0)
            previous = by_month.get(previous_month, 0.0)

            if previous == 0.0 and current > 0.0:
                flagged.append({
                    "vendor": vendor,
                    "previous_month_spend": 0.0,
                    "current_month_spend": round(current, 2),
                    "increase_pct": None,  # new vendor — no prior baseline
                })
            elif previous > 0.0:
                increase_pct = (current - previous) / previous
                if increase_pct >= SPIKE_THRESHOLD:
                    flagged.append({
                        "vendor": vendor,
                        "previous_month_spend": round(previous, 2),
                        "current_month_spend": round(current, 2),
                        "increase_pct": round(increase_pct * 100, 1),
                    })

        return {
            "analyzer": "vendor_spike",
            "spike_threshold_pct": SPIKE_THRESHOLD * 100,
            "current_month": str(current_month),
            "previous_month": str(previous_month),
            "flagged_count": len(flagged),
            "flagged_vendors": flagged,
        }
