"""
Views for the analytics app (Phase 6).

AnalysisRunView    POST /api/v1/analysis/run      → trigger an analysis
AnalysisResultsView GET /api/v1/analysis/results  → list past AnalysisRun records
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import AnalysisRun
from apps.analytics.serializers import AnalysisRunRequestSerializer, AnalysisRunSerializer
from apps.users.permissions import IsAdminOrOwner
from services.analysis_service import AnalysisService


class AnalysisRunView(APIView):
    """
    POST /api/v1/analysis/run

    Trigger a new analysis run for the authenticated user's organisation.
    Requires admin or owner role.
    """

    permission_classes = [IsAdminOrOwner]

    @extend_schema(
        tags=["Analysis"],
        summary="Trigger an analysis run",
        description=(
            "Runs the specified analyzer against all transactions for the authenticated "
            "user's organization. The run is persisted with status **SUCCEEDED** or "
            "**FAILED**. On success, alerts are automatically generated.\n\n"
            "Available `analysis_type` values: `large_transaction`, `burn_rate`, "
            "`vendor_spike`, `duplicate`."
        ),
        request=AnalysisRunRequestSerializer,
        responses={
            201: AnalysisRunSerializer,
            400: OpenApiResponse(description="Invalid request body or unknown `analysis_type`."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = AnalysisRunRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        org_id = request.user.organization_id
        analysis_type = serializer.validated_data["analysis_type"]

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


@extend_schema_view(
    get=extend_schema(
        tags=["Analysis"],
        summary="List analysis runs",
        description="Paginated list of AnalysisRun records for the authenticated user's organization, newest first.",
        parameters=[
            OpenApiParameter("analysis_type", str, description="Filter by analyzer key (e.g. `large_transaction`)."),
            OpenApiParameter("status", str, description="Filter by run status: `PENDING`, `SUCCEEDED`, or `FAILED`."),
        ],
    )
)
class AnalysisResultsView(ListAPIView):
    """
    GET /api/v1/analysis/results

    Return a paginated list of AnalysisRun records for the authenticated user's
    organization, newest first.

    Optional query parameters:
        ?analysis_type=<str>   — filter by analyzer key
        ?status=<str>          — filter by run status (PENDING/SUCCEEDED/FAILED)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisRunSerializer

    def get_queryset(self):
        qs = AnalysisRun.objects.select_related("organization").filter(
            organization_id=self.request.user.organization_id
        )

        analysis_type = self.request.query_params.get("analysis_type")
        if analysis_type:
            qs = qs.filter(analysis_type=analysis_type)

        run_status = self.request.query_params.get("status")
        if run_status:
            qs = qs.filter(status=run_status.upper())

        return qs


@extend_schema_view(
    get=extend_schema(
        tags=["Analysis"],
        summary="Retrieve an analysis run",
        description="Retrieve a single AnalysisRun record by its UUID, including full `results_summary`.",
        responses={
            200: AnalysisRunSerializer,
            404: OpenApiResponse(description="Analysis run not found."),
        },
    )
)
class AnalysisRunDetailView(RetrieveAPIView):
    """
    GET /api/v1/analysis/results/<uuid>/

    Retrieve a single AnalysisRun by its UUID, scoped to the user's organization.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisRunSerializer

    def get_queryset(self):
        return AnalysisRun.objects.select_related("organization").filter(
            organization_id=self.request.user.organization_id
        )
