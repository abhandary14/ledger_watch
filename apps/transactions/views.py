"""
Views for the transactions app.

Thin views — all business logic lives in TransactionService.
"""

from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.transactions.filters import TransactionFilter
from apps.transactions.models import Transaction
from apps.transactions.serializers import TransactionImportSerializer, TransactionSerializer
from apps.users.permissions import IsAdminOrOwner
from services.transaction_service import TransactionService


class TransactionImportView(APIView):
    """
    POST /api/v1/transactions/import

    Bulk-import a list of transactions for the authenticated user's organization.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Transactions"],
        summary="Bulk import transactions",
        description=(
            "Atomically imports a list of transactions for the authenticated user's "
            "organization. All rows are validated before any are persisted. "
            "An audit log entry is written on success."
        ),
        request=TransactionImportSerializer,
        responses={
            201: inline_serializer(
                "ImportResult",
                fields={"imported": serializers.IntegerField()},
            ),
            400: OpenApiResponse(description="Validation error — invalid fields or empty list."),
        },
    )
    def post(self, request):
        serializer = TransactionImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org_id = request.user.organization_id
        tx_data = serializer.validated_data["transactions"]

        created = TransactionService.bulk_import(str(org_id), tx_data)

        return Response(
            {"imported": len(created)},
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["Transactions"],
        summary="List transactions",
        description=(
            "Returns a paginated list of transactions for the authenticated user's "
            "organization (newest first). "
            "Supports filtering by vendor, category, and date range."
        ),
        parameters=[
            OpenApiParameter("vendor", str, description="Filter by vendor name (case-insensitive contains)."),
            OpenApiParameter("category", str, description="Filter by category (exact match)."),
            OpenApiParameter("date_from", str, description="Inclusive lower bound — YYYY-MM-DD."),
            OpenApiParameter("date_to", str, description="Inclusive upper bound — YYYY-MM-DD."),
        ],
    )
)
class TransactionListView(ListAPIView):
    """
    GET /api/v1/transactions/

    Paginated list of all transactions for the authenticated user's organization.
    Supports filtering via query params:
      ?vendor=    ?category=    ?date_from=YYYY-MM-DD    ?date_to=YYYY-MM-DD
    Supports ordering via ?ordering=date|-date|amount|-amount
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['date', 'amount', 'created_at']
    ordering = ['-date', '-created_at']

    def get_queryset(self):
        return Transaction.objects.select_related("organization").filter(
            organization_id=self.request.user.organization_id
        ).order_by('-date', '-created_at')


@extend_schema(
    tags=["Transactions"],
    summary="Get filter options",
    description="Returns distinct vendor names and category values for the authenticated user's organization.",
    responses={
        200: inline_serializer(
            "FilterOptions",
            fields={
                "vendors": serializers.ListField(child=serializers.CharField()),
                "categories": serializers.ListField(child=serializers.CharField()),
            },
        )
    },
)
class TransactionFilterOptionsView(APIView):
    """
    GET /api/v1/transactions/filter-options/

    Returns sorted lists of distinct vendor names and non-empty category values
    for the authenticated user's organization.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        org_id = request.user.organization_id
        qs = Transaction.objects.filter(organization_id=org_id).order_by()
        vendors = sorted(qs.values_list("vendor", flat=True).distinct())
        categories = sorted(
            v for v in qs.values_list("category", flat=True).distinct() if v
        )
        return Response({"vendors": vendors, "categories": categories})


@extend_schema_view(
    get=extend_schema(
        tags=["Transactions"],
        summary="Retrieve a transaction",
        description="Retrieve a single transaction by its UUID.",
        responses={
            200: TransactionSerializer,
            404: OpenApiResponse(description="Transaction not found."),
        },
    )
)
class TransactionDetailView(RetrieveAPIView):
    """
    GET /api/v1/transactions/{id}/

    Retrieve a single transaction by its UUID, scoped to the user's organization.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.select_related("organization").filter(
            organization_id=self.request.user.organization_id
        )


class TransactionDeleteView(APIView):
    """
    DELETE /api/v1/transactions/<uuid>/

    Permanently delete a transaction. Requires admin or owner role.
    """

    permission_classes = [IsAdminOrOwner]

    @extend_schema(
        tags=["Transactions"],
        summary="Delete a transaction",
        responses={
            204: OpenApiResponse(description="Transaction deleted."),
            404: OpenApiResponse(description="Transaction not found."),
        },
    )
    def delete(self, request, pk):
        with db_transaction.atomic():
            transaction = get_object_or_404(
                Transaction.objects.filter(
                    organization_id=request.user.organization_id
                ).select_for_update(),
                pk=pk,
            )

            AuditLog.objects.create(
                organization_id=transaction.organization_id,
                event_type="TRANSACTION_DELETED",
                metadata={
                    "transaction_id": str(transaction.id),
                    "vendor": transaction.vendor,
                    "amount": str(transaction.amount),
                    "date": str(transaction.date),
                    "deleted_by": str(request.user.id),
                },
            )

            transaction.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
