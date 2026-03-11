"""
TransactionService — business logic for ingesting transactions.

All DB writes and audit logging live here; views stay thin.
"""

from uuid import UUID

from django.db import transaction

from apps.audit.models import AuditLog
from apps.transactions.models import Transaction


class TransactionService:
    @staticmethod
    def bulk_import(org_id: UUID | str, data: list[dict]) -> list[Transaction]:
        """
        Persist a list of validated transaction dicts for the given org.

        Each dict must already be validated (e.g. via TransactionSerializer).
        Writes a TRANSACTION_IMPORTED AuditLog entry on success.
        Both writes are wrapped in a single atomic block so they commit or
        roll back together.

        Returns the list of created Transaction instances.
        """
        with transaction.atomic():
            instances = [
                Transaction(organization_id=org_id, **item)
                for item in data
            ]
            for instance in instances:
                instance.full_clean()
            created = Transaction.objects.bulk_create(instances)

            AuditLog.objects.create(
                organization_id=org_id,
                event_type="TRANSACTION_IMPORTED",
                metadata={"count": len(created)},
            )

        return created
