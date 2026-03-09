from django.contrib import admin

from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """
    Django admin configuration for the Organization model.
    Allows viewing and managing organizations via the /admin panel.
    """

    list_display = ["id", "name", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["id", "created_at"]
    ordering = ["name"]
