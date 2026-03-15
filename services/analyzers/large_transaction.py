"""
LargeTransactionAnalyzer — flags transactions that are abnormally large.

A transaction is flagged if its amount exceeds:
    max(2 × mean of all org transactions, HARD_FLOOR)

This catches both relatively large outliers within a normal-spending org
and absolutely large transactions for orgs with very low average spend.
"""

from uuid import UUID

from django.db.models import Avg

from apps.transactions.models import Transaction
from services.analyzers.base import Analyzer


class LargeTransactionAnalyzer(Analyzer):
    HARD_FLOOR = 10_000

    def run(self, organization_id: UUID | str) -> dict:
        txs = Transaction.objects.filter(organization_id=organization_id)
        avg = txs.aggregate(avg=Avg("amount"))["avg"] or 0
        threshold = max(float(avg) * 2, self.HARD_FLOOR)

        flagged = list(
            txs.filter(amount__gt=threshold)
            .values("id", "amount", "vendor", "date")
        )

        # Convert Decimal to float and UUID/date to str for JSON safety
        for tx in flagged:
            tx["id"] = str(tx["id"])
            tx["amount"] = float(tx["amount"])
            tx["date"] = str(tx["date"])

        return {
            "analyzer": "large_transaction",
            "threshold": threshold,
            "flagged_count": len(flagged),
            "flagged_transactions": flagged,
        }
