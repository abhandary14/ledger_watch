"""
Serializers for the alerts app (Phase 6).

AlertSerializer — serialises Alert objects for list / detail responses.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.alerts.models import Alert


class AlertSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for Alert records.

    ``organization_id`` is exposed directly (as a UUID string) instead of
    nesting the full organization object, keeping the response payload flat
    and consistent with the rest of the API.
    """

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "organization_id",
            "alert_type",
            "severity",
            "message",
            "status",
            "created_at",
        ]
        read_only_fields = fields
