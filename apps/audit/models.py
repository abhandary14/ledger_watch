import uuid

from django.db import models


class AuditLog(models.Model):
    """
    Immutable event log for significant system actions.

    ``AuditLog`` entries are written by ``TransactionService`` (and later by
    other services) to maintain a tamper-evident history of important events.
    They are intentionally schema-less (``metadata`` is a JSONField) so that
    any service can attach arbitrary context without a new migration.

    Design notes:
    - No ForeignKey to Organization — some events (e.g. seeding) may be
      org-agnostic. Callers embed org references inside ``metadata`` if needed.
    - No ``updated_at`` — audit logs must never be mutated after creation.
    - ``created_at`` is indexed implicitly via model ordering.

    Example event types: ``"TRANSACTION_IMPORTED"``, ``"ANALYSIS_RUN"``,
    ``"ALERT_ACKNOWLEDGED"``.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this audit log entry (UUID v4, auto-generated).",
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

    def __str__(self) -> str:
        return f"{self.event_type} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
