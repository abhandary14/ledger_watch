from rest_framework import serializers

from apps.organizations.models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Organization model.

    Handles conversion between Organization model instances and JSON.
    The `id` and `created_at` fields are read-only — they are set
    automatically by the database and should never be supplied by the caller.
    """

    class Meta:
        model = Organization
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]
