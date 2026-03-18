"""
URL configuration for the alerts app (Phase 6).

Mounted at api/v1/alerts/ in ledgerwatch/urls.py.
"""

from django.urls import path

from apps.alerts.views import (
    AlertAcknowledgeView,
    AlertDeleteView,
    AlertListView,
    AlertReopenView,
    AlertResolveView,
)

urlpatterns = [
    path("", AlertListView.as_view(), name="alert-list"),
    path("<uuid:pk>/acknowledge", AlertAcknowledgeView.as_view(), name="alert-acknowledge"),
    path("<uuid:pk>/resolve", AlertResolveView.as_view(), name="alert-resolve"),
    path("<uuid:pk>/reopen", AlertReopenView.as_view(), name="alert-reopen"),
    path("<uuid:pk>/delete", AlertDeleteView.as_view(), name="alert-delete"),
]
