"""
Views for the transactions app.

Thin views — all business logic lives in TransactionService.
"""

from rest_framework import status
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


class TransactionDetailView(RetrieveAPIView):
    """
    GET /api/v1/transactions/{id}/

    Retrieve a single transaction by its UUID.
    """

    serializer_class = TransactionSerializer
    queryset = Transaction.objects.select_related("organization").all()
