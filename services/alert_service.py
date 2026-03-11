"""
AlertService — interprets raw analyzer results and creates Alert objects.

Called by AnalysisService after every successful analyzer run.  Each
analyzer produces a structured results dict; AlertService maps those
structures to Alert severity levels and persists the records.

Severity mapping (from plan.md §6):
    Analyzer            │ Condition                        │ Severity
    ────────────────────┼──────────────────────────────────┼──────────
    large_transaction   │ amount > 5× mean                 │ HIGH
    large_transaction   │ amount 2–5× mean                 │ MEDIUM
    burn_rate           │ runway < 3 months                 │ HIGH
    burn_rate           │ runway 3–6 months                 │ MEDIUM
    burn_rate           │ net_monthly_burn > 0             │ LOW
    vendor_spike        │ increase_pct ≥ 50 %              │ MEDIUM
    vendor_spike        │ increase_pct 25–50 %             │ LOW
    vendor_spike        │ new vendor (increase_pct=None)   │ LOW
    duplicate           │ any duplicate group detected      │ LOW
"""

from __future__ import annotations

from uuid import UUID

from apps.alerts.models import Alert
from apps.audit.models import AuditLog


class AlertService:
    """
    Stateless service that converts analyzer results dicts into Alert rows.

    Every public method is a classmethod so callers never need to instantiate.
    """

    @classmethod
    def generate_alerts(
        cls,
        organization_id: UUID | str,
        analysis_type: str,
        results: dict,
    ) -> list[Alert]:
        """
        Dispatch to the correct alert-generation handler for *analysis_type*.

        Returns the list of Alert objects created (may be empty if no
        anomalies were found).  Each created Alert is also written to the
        AuditLog so there is an immutable record of when it was raised.
        """
        dispatch = {
            "large_transaction": cls._alerts_for_large_transaction,
            "burn_rate": cls._alerts_for_burn_rate,
            "vendor_spike": cls._alerts_for_vendor_spike,
            "duplicate": cls._alerts_for_duplicate,
        }

        handler = dispatch.get(analysis_type)
        if handler is None:
            # Unknown analyzer — nothing to do; don't raise so the run still
            # succeeds even if a custom analyzer hasn't registered a handler.
            return []

        alerts = handler(organization_id, results)
        cls._audit_alerts(organization_id, alerts)
        return alerts

    # ------------------------------------------------------------------
    # Per-analyzer handlers
    # ------------------------------------------------------------------

    @classmethod
    def _alerts_for_large_transaction(
        cls, organization_id: UUID | str, results: dict
    ) -> list[Alert]:
        """
        Create one Alert per flagged transaction.

        Severity is determined by comparing the transaction amount to the
        threshold that was recorded in the results dict:
            - threshold was set at max(2× mean, HARD_FLOOR)
            - amount > 5× mean  → HIGH  (i.e. amount > 2.5× threshold)
            - else              → MEDIUM
        """
        alerts: list[Alert] = []
        threshold: float = results.get("threshold", 0)

        for tx in results.get("flagged_transactions", []):
            amount: float = tx.get("amount", 0)
            # 5× mean = 2.5× threshold   (threshold = 2× mean)
            severity = (
                Alert.Severity.HIGH
                if threshold > 0 and amount > 2.5 * threshold
                else Alert.Severity.MEDIUM
            )
            message = (
                f"Transaction {tx['id']} from vendor '{tx['vendor']}' on {tx['date']} "
                f"has an unusually large amount of ${amount:,.2f} "
                f"(threshold: ${threshold:,.2f})."
            )
            alerts.append(
                Alert.objects.create(
                    organization_id=organization_id,
                    alert_type="large_transaction",
                    severity=severity,
                    message=message,
                )
            )
        return alerts

    @classmethod
    def _alerts_for_burn_rate(
        cls, organization_id: UUID | str, results: dict
    ) -> list[Alert]:
        """
        Create at most one Alert summarising the organisation's burn health.

        No alert is raised when the org is cash-flow positive (runway=None
        and net_monthly_burn ≤ 0).
        """
        net_burn: float = results.get("net_monthly_burn", 0)
        runway: float | None = results.get("runway_months")
        avg_expenses: float = results.get("avg_monthly_expenses", 0)
        avg_revenue: float = results.get("avg_monthly_revenue", 0)

        if net_burn <= 0:
            # Cash-flow positive — no alert needed.
            return []

        if runway is not None and runway < 3:
            severity = Alert.Severity.HIGH
            runway_str = f"{runway} month(s)"
        elif runway is not None and runway < 6:
            severity = Alert.Severity.MEDIUM
            runway_str = f"{runway} month(s)"
        else:
            severity = Alert.Severity.LOW
            runway_str = f"{runway} month(s)" if runway is not None else "unknown"

        message = (
            f"Monthly burn rate is ${net_burn:,.2f} "
            f"(avg expenses ${avg_expenses:,.2f} − avg revenue ${avg_revenue:,.2f}). "
            f"Estimated runway: {runway_str}."
        )
        return [
            Alert.objects.create(
                organization_id=organization_id,
                alert_type="burn_rate",
                severity=severity,
                message=message,
            )
        ]

    @classmethod
    def _alerts_for_vendor_spike(
        cls, organization_id: UUID | str, results: dict
    ) -> list[Alert]:
        """
        Create one Alert per flagged vendor.

        Severity:
            - increase_pct is None (new vendor)     → LOW
            - increase_pct ≥ 50 %                   → MEDIUM
            - 25 % ≤ increase_pct < 50 %            → LOW
        """
        alerts: list[Alert] = []
        current_month: str = results.get("current_month", "")
        previous_month: str = results.get("previous_month", "")

        for vendor_data in results.get("flagged_vendors", []):
            vendor: str = vendor_data["vendor"]
            increase_pct = vendor_data.get("increase_pct")  # float or None
            current_spend: float = vendor_data.get("current_month_spend", 0)
            previous_spend: float = vendor_data.get("previous_month_spend", 0)

            if increase_pct is None:
                severity = Alert.Severity.LOW
                message = (
                    f"New vendor '{vendor}' appeared in {current_month} "
                    f"with ${current_spend:,.2f} in spend (no prior month baseline)."
                )
            elif increase_pct >= 50:
                severity = Alert.Severity.MEDIUM
                message = (
                    f"Vendor '{vendor}' spend spiked {increase_pct:.1f}% "
                    f"from ${previous_spend:,.2f} ({previous_month}) "
                    f"to ${current_spend:,.2f} ({current_month})."
                )
            else:
                severity = Alert.Severity.LOW
                message = (
                    f"Vendor '{vendor}' spend increased {increase_pct:.1f}% "
                    f"from ${previous_spend:,.2f} ({previous_month}) "
                    f"to ${current_spend:,.2f} ({current_month})."
                )

            alerts.append(
                Alert.objects.create(
                    organization_id=organization_id,
                    alert_type="vendor_spike",
                    severity=severity,
                    message=message,
                )
            )
        return alerts

    @classmethod
    def _alerts_for_duplicate(
        cls, organization_id: UUID | str, results: dict
    ) -> list[Alert]:
        """
        Create one LOW-severity Alert per duplicate group detected.
        """
        alerts: list[Alert] = []
        window_hours: int = results.get("window_hours", 48)

        for group in results.get("duplicate_groups", []):
            vendor: str = group["vendor"]
            amount: float = group["amount"]
            tx_ids: list[str] = group["transaction_ids"]
            dates: list[str] = group["dates"]

            message = (
                f"Possible duplicate transactions detected for vendor '{vendor}': "
                f"{len(tx_ids)} transactions of ${amount:,.2f} each "
                f"within a {window_hours}-hour window "
                f"(dates: {', '.join(dates)}). "
                f"Transaction IDs: {', '.join(tx_ids)}."
            )
            alerts.append(
                Alert.objects.create(
                    organization_id=organization_id,
                    alert_type="duplicate",
                    severity=Alert.Severity.LOW,
                    message=message,
                )
            )
        return alerts

    # ------------------------------------------------------------------
    # Audit helper
    # ------------------------------------------------------------------

    @classmethod
    def _audit_alerts(
        cls, organization_id: UUID | str, alerts: list[Alert]
    ) -> None:
        """Write one AuditLog entry summarising all alerts raised in a batch."""
        if not alerts:
            return
        AuditLog.objects.create(
            organization_id=organization_id,
            event_type="ALERTS_GENERATED",
            metadata={
                "alert_count": len(alerts),
                "alert_ids": [str(a.id) for a in alerts],
                "alert_types": list({a.alert_type for a in alerts}),
            },
        )
