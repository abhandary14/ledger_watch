"""
Serializers for the analytics app (Phase 6).

AnalysisRunRequestSerializer  — validates incoming POST /api/v1/analysis/run
AnalysisRunSerializer         — serialises AnalysisRun for GET responses
"""

from __future__ import annotations

from rest_framework import serializers

from apps.analytics.models import AnalysisRun
from factories.analyzer_factory import AnalyzerFactory


class AnalysisRunRequestSerializer(serializers.Serializer):
    """
    Validates the body of POST /api/v1/analysis/run.

    Expected JSON::

        {
            "organization_id": "<uuid>",
            "analysis_type": "large_transaction"
        }
    """

    organization_id = serializers.UUIDField(
        help_text="UUID of the organization to run the analysis against.",
    )
    analysis_type = serializers.ChoiceField(
        choices=AnalyzerFactory.available(),
        help_text=(
            "Analyzer key to run. "
            f"Available: {', '.join(AnalyzerFactory.available())}."
        ),
    )


class AnalysisRunSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for AnalysisRun records returned from GET endpoints.
    """

    organization_id = serializers.UUIDField(source="organization.id", read_only=True)

    class Meta:
        model = AnalysisRun
        fields = [
            "id",
            "organization_id",
            "analysis_type",
            "status",
            "run_time",
            "results_summary",
            "error_message",
        ]
        read_only_fields = fields
