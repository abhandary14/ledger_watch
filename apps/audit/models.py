import uuid

from django.core.exceptions import PermissionDenied
from django.db import models

from apps.organizations.models import Organization


class AuditLog(models.Model):
    """
    Immutable, write-once event log for significant system actions.

    ``AuditLog`` entries are written by services (e.g. ``TransactionService``)
    to maintain a tamper-evident history. Once created, records cannot be
    updated or deleted — enforced at the ORM level via overridden save() and
    delete() methods.

    Design notes:
    - ``organization`` is a nullable FK so org-agnostic events (e.g. seeding)
      can still be logged, while org-scoped events carry a proper FK reference
      for indexed lookups.
    - No ``updated_at`` — audit logs must never be mutated after creation.
    - No explicit index on ``created_at`` — add one if query volume warrants it.

    Example event types: ``"TRANSACTION_IMPORTED"``, ``"ANALYSIS_RUN"``,
    ``"ALERT_ACKNOWLEDGED"``.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this audit log entry (UUID v4, auto-generated).",
    )
    organization = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_index=True,
        related_name="audit_logs",
        help_text=(
            "Organization this event is scoped to, if applicable. "
            "Null for system-wide or org-agnostic events."
        ),
    )
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Machine-readable event identifier (e.g. 'TRANSACTION_IMPORTED').",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Arbitrary JSON payload providing event context.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this log entry was created. Set automatically.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    # ------------------------------------------------------------------
    # Write-once enforcement
    # ------------------------------------------------------------------

    def save(self, *args, **kwargs) -> None:
        """Allow INSERT only. Raises PermissionDenied on UPDATE attempts."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionDenied(
                f"AuditLog records are immutable. "
                f"Attempted update on pk={self.pk}."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        """Block all deletion attempts at the ORM level."""
        raise PermissionDenied(
            f"AuditLog records cannot be deleted. pk={self.pk}."
        )

    @classmethod
    def _base_manager_delete(cls, queryset) -> None:
        """Block bulk queryset deletes (e.g. org.audit_logs.all().delete())."""
        raise PermissionDenied("Bulk deletion of AuditLog records is not permitted.")

    def __str__(self) -> str:
        # created_at is auto_now_add so it is None on unsaved instances.
        ts = self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "unsaved"
        return f"{self.event_type} @ {ts}"