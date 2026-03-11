"""
URL configuration for the analytics app (Phase 6).

Mounted at api/v1/analysis/ in ledgerwatch/urls.py.
"""

from django.urls import path

from apps.analytics.views import AnalysisResultsView, AnalysisRunDetailView, AnalysisRunView

urlpatterns = [
    # POST  api/v1/analysis/run          — trigger a new analysis run
    path("run", AnalysisRunView.as_view(), name="analysis-run"),

    # GET   api/v1/analysis/results      — list all AnalysisRun records
    path("results", AnalysisResultsView.as_view(), name="analysis-results"),

    # GET   api/v1/analysis/results/<uuid>/  — retrieve a single AnalysisRun
    path("results/<uuid:pk>/", AnalysisRunDetailView.as_view(), name="analysis-run-detail"),
]
