from django.urls import path

from apps.transactions.views import (
    TransactionDeleteView,
    TransactionDetailView,
    TransactionFilterOptionsView,
    TransactionImportView,
    TransactionListView,
)

urlpatterns = [
    path("import", TransactionImportView.as_view(), name="transaction-import"),
    path("filter-options/", TransactionFilterOptionsView.as_view(), name="transaction-filter-options"),
    path("", TransactionListView.as_view(), name="transaction-list"),
    path("<uuid:pk>/", TransactionDetailView.as_view(), name="transaction-detail"),
    path("<uuid:pk>/delete", TransactionDeleteView.as_view(), name="transaction-delete"),
]
