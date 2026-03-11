"""
TransactionService — business logic for ingesting transactions.

All DB writes and audit logging live here; views stay thin.
"""

from apps.audit.models import AuditLog
from apps.transactions.models import Transaction


class TransactionService:
    @staticmethod
    def bulk_import(org_id: str, data: list[dict]) -> list[Transaction]:
        """
        Persist a list of validated transaction dicts for the given org.

        Each dict must already be validated (e.g. via TransactionSerializer).
        Writes an TRANSACTION_IMPORTED AuditLog entry on success.

        Returns the list of created Transaction instances.
        """
        transactions = [
            Transaction(organization_id=org_id, **item)
            for item in data
        ]
        created = Transaction.objects.bulk_create(transactions)

        AuditLog.objects.create(
            organization_id=org_id,
            event_type="TRANSACTION_IMPORTED",
            metadata={"count": len(created)},
        )

        return created
