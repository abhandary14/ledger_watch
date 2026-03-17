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
    """Read serializer for a single Transaction."""

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)

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
        read_only_fields = fields

    def validate_amount(self, value):
        return validate_positive_amount(value)


class TransactionRowSerializer(serializers.ModelSerializer):
    """
    Validates a single row inside a bulk-import request body.

    ``organization_id`` is not accepted here — it is derived from the
    authenticated user's organization, not from the request body.
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
            "transactions": [ { ...transaction fields... }, ... ]
        }

    ``organization_id`` is no longer accepted in the body — it is derived
    from the authenticated user's organization.
    """

    transactions = TransactionRowSerializer(many=True)

    def validate_transactions(self, value):
        if not value:
            raise serializers.ValidationError("At least one transaction is required.")
        return value
