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
    """

    class Meta:
        model = Alert
        fields = [
            "id",
            "alert_type",
            "severity",
            "message",
            "status",
            "created_at",
        ]
        read_only_fields = fields
