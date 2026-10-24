from rest_framework import serializers

from apps.reports.models import ReportRun


class ReportRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportRun
        fields = [
            "id",
            "generated_at",
            "report_path",
            "alert_count",
            "triggered_by",
            "status",
            "error_message",
        ]
        read_only_fields = fields
