"""
LedgerWatch root URL configuration.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from ledgerwatch.views import health

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Health check
    path("health", health, name="health"),

    # OpenAPI schema + docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # App routes (added per phase)
    path("api/v1/transactions/", include("apps.transactions.urls")),
    path("api/v1/analysis/", include("apps.analytics.urls")),
    path("api/v1/alerts/", include("apps.alerts.urls")),
]
