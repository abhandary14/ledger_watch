from django.urls import path

from apps.reports.views import GenerateReportView

urlpatterns = [
    path("generate", GenerateReportView.as_view(), name="report-generate"),
]
