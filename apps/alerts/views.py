"""
Views for the alerts app (Phase 6).

AlertListView        GET  /api/v1/alerts/                  — list all alerts
AlertAcknowledgeView POST /api/v1/alerts/<uuid>/acknowledge — mark ACKNOWLEDGED
AlertResolveView     POST /api/v1/alerts/<uuid>/resolve     — mark RESOLVED
"""

from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.alerts.serializers import AlertSerializer
from apps.audit.models import AuditLog


class AlertListView(ListAPIView):
    """
    GET /api/v1/alerts/

    Return a paginated list of all Alert records, newest first.

    Optional query parameters:
        ?organization_id=<uuid>   — filter by organisation
        ?alert_type=<str>         — filter by analyzer key (e.g. 'large_transaction')
        ?severity=<str>           — filter by severity (LOW / MEDIUM / HIGH)
        ?status=<str>             — filter by status  (OPEN / ACKNOWLEDGED / RESOLVED)
    """

    serializer_class = AlertSerializer

    def get_queryset(self):
        qs = Alert.objects.select_related("organization").all()

        org_id = self.request.query_params.get("organization_id")
        if org_id:
            qs = qs.filter(organization_id=org_id)

        alert_type = self.request.query_params.get("alert_type")
        if alert_type:
            qs = qs.filter(alert_type=alert_type)

        severity = self.request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity.upper())

        alert_status = self.request.query_params.get("status")
        if alert_status:
            qs = qs.filter(status=alert_status.upper())

        return qs


class AlertAcknowledgeView(APIView):
    """
    POST /api/v1/alerts/<uuid>/acknowledge

    Transition an alert from OPEN → ACKNOWLEDGED.

    Only OPEN alerts may be acknowledged.  Attempting to acknowledge an
    already-acknowledged or resolved alert returns HTTP 409 Conflict.
    """

    def post(self, request: Request, pk) -> Response:
        with transaction.atomic():
            alert = get_object_or_404(Alert.objects.select_for_update(), pk=pk)

            if alert.status != Alert.Status.OPEN:
                return Response(
                    {
                        "detail": (
                            f"Alert is already {alert.status} and cannot be acknowledged. "
                            "Only OPEN alerts can be acknowledged."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            alert.status = Alert.Status.ACKNOWLEDGED
            alert.save(update_fields=["status"])

            AuditLog.objects.create(
                organization_id=alert.organization_id,
                event_type="ALERT_ACKNOWLEDGED",
                metadata={"alert_id": str(alert.id), "alert_type": alert.alert_type},
            )

        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)


class AlertResolveView(APIView):
    """
    POST /api/v1/alerts/<uuid>/resolve

    Transition an alert from OPEN or ACKNOWLEDGED → RESOLVED.

    Attempting to resolve an already-resolved alert returns HTTP 409 Conflict.
    """

    def post(self, request: Request, pk) -> Response:
        with transaction.atomic():
            alert = get_object_or_404(Alert.objects.select_for_update(), pk=pk)

            if alert.status == Alert.Status.RESOLVED:
                return Response(
                    {"detail": "Alert is already RESOLVED."},
                    status=status.HTTP_409_CONFLICT,
                )

            alert.status = Alert.Status.RESOLVED
            alert.save(update_fields=["status"])

            AuditLog.objects.create(
                organization_id=alert.organization_id,
                event_type="ALERT_RESOLVED",
                metadata={"alert_id": str(alert.id), "alert_type": alert.alert_type},
            )

        return Response(AlertSerializer(alert).data, status=status.HTTP_200_OK)
