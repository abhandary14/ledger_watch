import uuid

from django.db import models


class Organization(models.Model):
    """
    Represents a business entity using LedgerWatch.

    Every Transaction, Alert, and AnalysisRun is scoped to an Organization.
    This is the top-level tenant in the system.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the organization (UUID v4, auto-generated).",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name of the organization (e.g. 'Acme Corp').",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the organization record was created. Set automatically.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self) -> str:
        return self.name
