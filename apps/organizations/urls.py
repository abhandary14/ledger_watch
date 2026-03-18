"""
URL configuration for the organizations app.

Mounted at api/v1/organizations/ in ledgerwatch/urls.py.
"""

from django.urls import path

from apps.organizations.views import (
    OrgMemberDetailView,
    OrgMemberListCreateView,
    OrganizationDetailView,
    SecurityChallengeView,
    TransferOwnershipView,
)

urlpatterns = [
    path("<uuid:pk>/", OrganizationDetailView.as_view(), name="organization-detail"),
    path("members/", OrgMemberListCreateView.as_view(), name="org-member-list-create"),
    path("members/<uuid:pk>/", OrgMemberDetailView.as_view(), name="org-member-detail"),
    path("transfer-ownership/", TransferOwnershipView.as_view(), name="transfer-ownership"),
    path("security-challenge/", SecurityChallengeView.as_view(), name="security-challenge"),
]
