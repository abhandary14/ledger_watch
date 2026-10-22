"""
BurnRateAnalyzer — calculates monthly burn rate and estimated runway.

Logic:
- Revenue: transactions in the "Revenue" category, matched case-insensitively and
  ignoring surrounding whitespace ("revenue", " REVENUE " also count).
- Expenses: transactions with amount > 0 that are NOT revenue.
- Monthly net burn = average monthly expenses - average monthly revenue.
- Runway months = average monthly revenue / net burn.
  If net burn <= 0, the org is cash-flow positive (runway reported as None).
"""

from django.db.models import F, Func, Sum, Value
from django.db.models.functions import Lower, TruncMonth

from apps.transactions.models import Transaction
from services.analyzers.base import Analyzer


class BurnRateAnalyzer(Analyzer):
    REVENUE_CATEGORY = "Revenue"

    def run(self) -> dict:
        # Normalise the category so "revenue" / " Revenue " are recognised too.
        # REGEXP_REPLACE rather than Trim: PostgreSQL TRIM() strips spaces only, not tabs/newlines.
        stripped = Func(F("category"), Value(r"^\s+|\s+$"), Value(""), Value("g"), function="REGEXP_REPLACE")
        txs = Transaction.objects.annotate(category_key=Lower(stripped))
        revenue_key = self.REVENUE_CATEGORY.lower()

        # Aggregate expenses and revenue per calendar month
        expense_by_month = (
            txs.exclude(category_key=revenue_key)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
        )
        revenue_by_month = (
            txs.filter(category_key=revenue_key)
            .annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
        )

        expense_map = {r["month"]: float(r["total"]) for r in expense_by_month}
        revenue_map = {r["month"]: float(r["total"]) for r in revenue_by_month}

        # Use the union of months so both averages share the same denominator.
        # Months with no expenses or no revenue contribute 0 to their respective sum.
        all_months = expense_map.keys() | revenue_map.keys()
        n = len(all_months)

        avg_monthly_expenses = (
            sum(expense_map.get(m, 0.0) for m in all_months) / n if n else 0.0
        )
        avg_monthly_revenue = (
            sum(revenue_map.get(m, 0.0) for m in all_months) / n if n else 0.0
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
