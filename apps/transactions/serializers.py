"""
Serializers for the transactions app.
"""

from rest_framework import serializers

from apps.transactions.models import Transaction


def validate_positive_amount(value):
    if value <= 0:
        raise serializers.ValidationError("Amount must be greater than zero.")
    return value


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializes / deserializes a single Transaction.

    ``organization`` is exposed as a write-only UUID field on input so callers
    supply the org ID directly.  On output it is rendered as the UUID string.
    """

    organization_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "organization_id",
            "date",
            "vendor",
            "amount",
            "description",
            "category",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_amount(self, value):
        return validate_positive_amount(value)


class TransactionRowSerializer(serializers.ModelSerializer):
    """
    Validates a single row inside a bulk-import request body.

    Identical to TransactionSerializer but omits ``organization_id`` — the
    org is supplied once at the top level of the import payload, not repeated
    per row.
    """

    class Meta:
        model = Transaction
        fields = ["date", "vendor", "amount", "description", "category"]

    def validate_amount(self, value):
        return validate_positive_amount(value)


class TransactionImportSerializer(serializers.Serializer):
    """
    Wraps a list of transactions for the bulk-import endpoint.

    Expected request body:
        {
            "organization_id": "<uuid>",
            "transactions": [ { ...transaction fields... }, ... ]
        }
    """

    organization_id = serializers.UUIDField()
    transactions = TransactionRowSerializer(many=True)

    def validate_transactions(self, value):
        if not value:
            raise serializers.ValidationError("At least one transaction is required.")
        return value
