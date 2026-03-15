"""
Views for the transactions app.

Thin views — all business logic lives in TransactionService.
"""

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.transactions.filters import TransactionFilter
from apps.transactions.models import Transaction
from apps.transactions.serializers import TransactionImportSerializer, TransactionSerializer
from services.transaction_service import TransactionService


class TransactionImportView(APIView):
    """
    POST /api/v1/transactions/import

    Bulk-import a list of transactions for an organization.
    """

    @extend_schema(
        tags=["Transactions"],
        summary="Bulk import transactions",
        description=(
            "Atomically imports a list of transactions for the given organization. "
            "All rows are validated before any are persisted. "
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

        org_id = serializer.validated_data["organization_id"]
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
            "Returns a paginated list of all transactions (newest first). "
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

    Paginated list of all transactions. Supports filtering via query params:
      ?vendor=    ?category=    ?date_from=YYYY-MM-DD    ?date_to=YYYY-MM-DD
    """

    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter

    def get_queryset(self):
        return Transaction.objects.select_related("organization").all()


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

    Retrieve a single transaction by its UUID.
    """

    serializer_class = TransactionSerializer
    queryset = Transaction.objects.select_related("organization").all()
