from rest_framework import serializers

from apps.reports.models import ReportRun


class ReportRunSerializer(serializers.ModelSerializer):
    organization_id = serializers.UUIDField(source="organization.id", read_only=True)

    class Meta:
        model = ReportRun
        fields = [
            "id",
            "organization_id",
            "generated_at",
            "report_path",
            "alert_count",
            "triggered_by",
            "status",
            "error_message",
        ]
        read_only_fields = fields
