"""
Views for the analytics app (Phase 6).

AnalysisRunView    POST /api/v1/analysis/run      → trigger an analysis
AnalysisResultsView GET /api/v1/analysis/results  → list past AnalysisRun records
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import AnalysisRun
from apps.analytics.serializers import AnalysisRunRequestSerializer, AnalysisRunSerializer
from apps.organizations.models import Organization
from services.analysis_service import AnalysisService


class AnalysisRunView(APIView):
    """
    POST /api/v1/analysis/run

    Trigger a new analysis run for an organisation.

    Request body::

        {
            "organization_id": "<uuid>",
            "analysis_type": "large_transaction"
        }

    Responses:
        201 Created        — run completed (SUCCEEDED or FAILED — both are persisted).
        400 Bad Request    — invalid body or unknown analyzer type.
        404 Not Found      — organization_id not in DB.
    """

    def post(self, request: Request) -> Response:
        serializer = AnalysisRunRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        org_id = serializer.validated_data["organization_id"]
        analysis_type = serializer.validated_data["analysis_type"]

        # Confirm the organization exists — return 404 rather than a DB IntegrityError.
        get_object_or_404(Organization, pk=org_id)

        try:
            run = AnalysisService.run_analysis(
                organization_id=org_id,
                analysis_type=analysis_type,
            )
        except ValueError as exc:
            # AnalyzerFactory.create() raised — unknown analysis_type.
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        out = AnalysisRunSerializer(run)
        return Response(out.data, status=status.HTTP_201_CREATED)


class AnalysisResultsView(ListAPIView):
    """
    GET /api/v1/analysis/results

    Return a paginated list of all AnalysisRun records, newest first.

    Optional query parameters:
        ?organization_id=<uuid>   — filter by organisation
        ?analysis_type=<str>      — filter by analyzer key
        ?status=<str>             — filter by run status (PENDING/SUCCEEDED/FAILED)
    """

    serializer_class = AnalysisRunSerializer

    def get_queryset(self):
        qs = AnalysisRun.objects.select_related("organization").all()

        org_id = self.request.query_params.get("organization_id")
        if org_id:
            qs = qs.filter(organization_id=org_id)

        analysis_type = self.request.query_params.get("analysis_type")
        if analysis_type:
            qs = qs.filter(analysis_type=analysis_type)

        run_status = self.request.query_params.get("status")
        if run_status:
            qs = qs.filter(status=run_status.upper())

        return qs


class AnalysisRunDetailView(RetrieveAPIView):
    """
    GET /api/v1/analysis/results/<uuid>/

    Retrieve a single AnalysisRun by its UUID.
    """

    serializer_class = AnalysisRunSerializer
    queryset = AnalysisRun.objects.select_related("organization").all()
