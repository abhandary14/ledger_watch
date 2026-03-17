from django.urls import path

from apps.organizations.views import OrganizationDetailView

urlpatterns = [
    path("<uuid:pk>/", OrganizationDetailView.as_view(), name="organization-detail"),
]
