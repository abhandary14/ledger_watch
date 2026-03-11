from django.urls import path

from apps.transactions.views import (
    TransactionDetailView,
    TransactionImportView,
    TransactionListView,
)

urlpatterns = [
    path("import", TransactionImportView.as_view(), name="transaction-import"),
    path("", TransactionListView.as_view(), name="transaction-list"),
    path("<uuid:pk>/", TransactionDetailView.as_view(), name="transaction-detail"),
]
