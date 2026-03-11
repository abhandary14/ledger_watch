"""
Serializers for the transactions app.
"""

from rest_framework import serializers

from apps.transactions.models import Transaction


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
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


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
    transactions = TransactionSerializer(many=True)

    def validate_transactions(self, value):
        if not value:
            raise serializers.ValidationError("At least one transaction is required.")
        return value
