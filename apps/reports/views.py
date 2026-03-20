from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reports.serializers import ReportRunSerializer
from apps.users.permissions import IsOwner
from services.report_service import ReportService


class GenerateReportView(APIView):
    """
    POST /api/v1/reports/generate

    Runs all four analyzers, collects unreported alerts, calls Claude to
    generate a narrative, and renders a PDF report.
    Requires owner role.
    """

    permission_classes = [IsOwner]

    @extend_schema(
        tags=["Reports"],
        summary="Generate a weekly financial risk report",
        description=(
            "Runs all four analyzers (skipping already-current types), collects unreported "
            "alerts, builds a narrative using Claude AI, and renders a PDF. "
            "Returns 200 with report metadata on success, or 200 with `report: null` if "
            "there are no new alerts to report."
        ),
        responses={
            200: ReportRunSerializer,
            503: OpenApiResponse(description="Claude API key not configured."),
            500: OpenApiResponse(description="Report generation failed."),
        },
    )
    def post(self, request: Request) -> Response:
        org_id = request.user.organization_id
        try:
            report_run = ReportService.generate_report(
                organization_id=org_id,
                triggered_by="manual",
            )
        except ImproperlyConfigured:
            return Response(
                {"detail": "Claude API key not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            return Response(
                {"detail": f"Report generation failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if report_run is None:
            return Response(
                {"detail": "No new alerts since last report.", "report": None},
                status=status.HTTP_200_OK,
            )

        return Response(ReportRunSerializer(report_run).data, status=status.HTTP_200_OK)
