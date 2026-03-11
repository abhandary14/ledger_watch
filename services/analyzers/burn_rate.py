"""
BurnRateAnalyzer — calculates monthly burn rate and estimated runway.

Logic:
- Expenses: transactions with amount > 0 that are NOT in the "Revenue" category.
- Revenue: transactions in the "Revenue" category.
- Monthly net burn = average monthly expenses - average monthly revenue.
- Runway months = total remaining cash proxy (last month's revenue) / net burn.
  If net burn <= 0, the org is cash-flow positive (runway reported as None).
"""

from uuid import UUID

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from apps.transactions.models import Transaction
from services.analyzers.base import Analyzer


class BurnRateAnalyzer(Analyzer):
    REVENUE_CATEGORY = "Revenue"

    def run(self, organization_id: UUID | str) -> dict:
        txs = Transaction.objects.filter(organization_id=organization_id)

        # Aggregate expenses and revenue per calendar month
        expense_by_month = (
            txs.exclude(category=self.REVENUE_CATEGORY)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
        )
        revenue_by_month = (
            txs.filter(category=self.REVENUE_CATEGORY)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
        )

        expense_totals = [float(r["total"]) for r in expense_by_month]
        revenue_totals = [float(r["total"]) for r in revenue_by_month]

        avg_monthly_expenses = (
            sum(expense_totals) / len(expense_totals) if expense_totals else 0.0
        )
        avg_monthly_revenue = (
            sum(revenue_totals) / len(revenue_totals) if revenue_totals else 0.0
        )

        net_burn = avg_monthly_expenses - avg_monthly_revenue
        runway_months = None if net_burn <= 0 else round(avg_monthly_revenue / net_burn, 1)

        return {
            "analyzer": "burn_rate",
            "avg_monthly_expenses": round(avg_monthly_expenses, 2),
            "avg_monthly_revenue": round(avg_monthly_revenue, 2),
            "net_monthly_burn": round(net_burn, 2),
            "runway_months": runway_months,
        }
