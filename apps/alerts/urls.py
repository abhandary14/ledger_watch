"""
URL configuration for the alerts app (Phase 6).

Mounted at api/v1/alerts/ in ledgerwatch/urls.py.
"""

from django.urls import path

from apps.alerts.views import AlertAcknowledgeView, AlertListView, AlertReopenView, AlertResolveView

urlpatterns = [
    # GET  api/v1/alerts/                        — list all alerts (with filters)
    path("", AlertListView.as_view(), name="alert-list"),

    # POST api/v1/alerts/<uuid>/acknowledge      — mark alert as ACKNOWLEDGED
    path("<uuid:pk>/acknowledge", AlertAcknowledgeView.as_view(), name="alert-acknowledge"),

    # POST api/v1/alerts/<uuid>/resolve          — mark alert as RESOLVED
    path("<uuid:pk>/resolve", AlertResolveView.as_view(), name="alert-resolve"),

    # POST api/v1/alerts/<uuid>/reopen           — reopen a RESOLVED alert (admin/owner only)
    path("<uuid:pk>/reopen", AlertReopenView.as_view(), name="alert-reopen"),
]
