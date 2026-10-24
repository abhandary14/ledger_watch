"""
JWT-based tenant resolution middleware for django-tenants.

Unlike the default TenantMainMiddleware (which resolves from subdomain),
this middleware resolves the tenant from the authenticated user's organization.
Unauthenticated endpoints (login, register, health) use the public schema.
"""

from django.db import connection
from django_tenants.middleware import TenantMainMiddleware

from apps.organizations.models import Organization


class JWTTenantMiddleware(TenantMainMiddleware):
    """
    Resolve tenant from JWT-authenticated user's organization.

    Request lifecycle:
    1. Middleware sets public schema as default (all requests start here).
    2. After DRF authentication runs, the view/service calls
       ``set_tenant_from_user(request)`` to switch to the tenant schema.
    3. On unauthenticated endpoints, the schema stays public.

    This two-phase approach is necessary because JWT authentication happens
    inside DRF's view layer, AFTER middleware runs. Middleware cannot decode
    the JWT token itself without duplicating DRF's auth pipeline.
    """

    def process_request(self, request):
        connection.set_schema_to_public()
        # There is no public tenant row; the real tenant is set after JWT auth.
        request.tenant = None


def set_tenant_from_user(request):
    """
    Switch the DB connection to the authenticated user's tenant schema.

    Call this at the start of any authenticated view or in a DRF
    authentication mixin after ``request.user`` is resolved.

    Raises Organization.DoesNotExist if the user's org has no schema.
    """
    org = Organization.objects.get(pk=request.user.organization_id)
    connection.set_tenant(org)
    request.tenant = org
