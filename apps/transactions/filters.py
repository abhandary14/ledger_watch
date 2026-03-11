"""
django-filter FilterSet for Transaction list queries.
"""

import django_filters

from apps.transactions.models import Transaction


class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Transaction
        fields = ["vendor", "category", "date_from", "date_to"]
