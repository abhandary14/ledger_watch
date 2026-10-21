"""
DRF view mixin that switches to the tenant schema after authentication.
"""

from django.db import connection

from apps.organizations.models import Organization


class TenantViewMixin:
    """
    DRF view mixin that switches to the tenant schema after authentication.

    Add this as the FIRST parent class of any view that requires tenant context.
    For unauthenticated views (login, register, health), do not use this mixin.
    """

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user and request.user.is_authenticated:
            org = Organization.objects.get(pk=request.user.organization_id)
            connection.set_tenant(org)
            request.tenant = org
