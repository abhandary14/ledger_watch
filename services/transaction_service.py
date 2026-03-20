"""
TransactionService — business logic for ingesting transactions.

All DB writes and audit logging live here; views stay thin.
"""

from uuid import UUID

from django.db import transaction
from django.db.models import Q

from apps.audit.models import AuditLog
from apps.transactions.models import Transaction


class DuplicateImportError(Exception):
    """Raised when all rows in an import batch already exist."""

    pass


class TransactionService:
    @staticmethod
    def bulk_import(org_id: UUID | str, data: list[dict]) -> dict:
        """
        Persist a list of validated transaction dicts for the given org,
        skipping rows that already exist (same date, vendor, amount).

        Each dict must already be validated (e.g. via TransactionSerializer).
        Writes a TRANSACTION_IMPORTED AuditLog entry on success.
        Both writes are wrapped in a single atomic block so they commit or
        roll back together.

        Returns a dict with 'created' (list[Transaction]) and 'skipped' (int).
        Raises DuplicateImportError if every row is a duplicate.
        """
        # Build a Q filter to find existing transactions that match any incoming row.
        duplicate_q = Q()
        for item in data:
            duplicate_q |= Q(date=item["date"], vendor=item["vendor"], amount=item["amount"])

        existing = set(
            Transaction.objects.filter(
                Q(organization_id=org_id) & duplicate_q
            ).values_list("date", "vendor", "amount")
        )

        new_data = [
            item for item in data
            if (item["date"], item["vendor"], item["amount"]) not in existing
        ]

        skipped = len(data) - len(new_data)

        if not new_data:
            raise DuplicateImportError(
                "All transactions in this file have already been imported."
            )

        with transaction.atomic():
            instances = [
                Transaction(organization_id=org_id, **item)
                for item in new_data
            ]
            for instance in instances:
                instance.full_clean()
            created = Transaction.objects.bulk_create(instances)

            AuditLog.objects.create(
                organization_id=org_id,
                event_type="TRANSACTION_IMPORTED",
                metadata={"count": len(created), "skipped_duplicates": skipped},
            )

        return {"created": created, "skipped": skipped}
