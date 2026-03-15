"""
DuplicateTransactionAnalyzer — finds likely duplicate transactions.

Logic:
- Two transactions are considered duplicates if they share the same vendor
  and amount and were created within WINDOW_HOURS of each other.
- Returns each group of duplicates as a list of transaction IDs.
"""

from datetime import timedelta
from uuid import UUID

from apps.transactions.models import Transaction
from services.analyzers.base import Analyzer

WINDOW_HOURS = 48


class DuplicateTransactionAnalyzer(Analyzer):
    def run(self, organization_id: UUID | str) -> dict:
        txs = list(
            Transaction.objects.filter(organization_id=organization_id)
            .values("id", "vendor", "amount", "date", "created_at")
            .order_by("vendor", "amount", "created_at")
        )

        duplicate_groups = []
        visited: set = set()

        for i, tx in enumerate(txs):
            if tx["id"] in visited:
                continue

            group = [tx]
            for j in range(i + 1, len(txs)):
                other = txs[j]
                if other["vendor"] != tx["vendor"] or other["amount"] != tx["amount"]:
                    break
                delta = abs(other["created_at"] - tx["created_at"])
                if delta <= timedelta(hours=WINDOW_HOURS):
                    group.append(other)
                    visited.add(other["id"])

            if len(group) > 1:
                visited.add(tx["id"])
                duplicate_groups.append({
                    "vendor": tx["vendor"],
                    "amount": float(tx["amount"]),
                    "transaction_ids": [str(t["id"]) for t in group],
                    "dates": [str(t["date"]) for t in group],
                })

        return {
            "analyzer": "duplicate",
            "window_hours": WINDOW_HOURS,
            "duplicate_group_count": len(duplicate_groups),
            "duplicate_groups": duplicate_groups,
        }
