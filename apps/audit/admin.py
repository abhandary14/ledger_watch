from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Read-only admin view for AuditLog.

    Audit log entries are immutable — no add, change, or delete actions
    are permitted through the admin interface.
    """

    list_display = ["event_type", "organization", "created_at"]
    list_filter = ["event_type", "organization"]
    search_fields = ["event_type", "metadata"]
    ordering = ["-created_at"]

    # Make every field read-only so the change form is purely for inspection.
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.get_fields()]

    # ------------------------------------------------------------------
    # Strip all write permissions from the admin
    # ------------------------------------------------------------------

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
