import uuid

from django.db import models

from apps.organizations.models import Organization


class ReportRun(models.Model):
    """
    Audit record for a single report generation attempt.

    Created by ``ReportService.generate_report()`` on completion (SUCCEEDED or FAILED).
    PENDING is reserved for future async use.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this report run (UUID v4, auto-generated).",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="report_runs",
        help_text="The organization this report was generated for.",
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this report run record was created.",
    )
    report_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path to the generated PDF under REPORT_OUTPUT_DIR.",
    )
    alert_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of alerts included in this report.",
    )
    triggered_by = models.CharField(
        max_length=20,
        default="manual",
        help_text="How this report was triggered: 'scheduled' or 'manual'.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Lifecycle status: PENDING, SUCCEEDED, or FAILED.",
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text="Exception detail if status=FAILED.",
    )

    class Meta:
        ordering = ["-generated_at"]
        verbose_name = "Report Run"
        verbose_name_plural = "Report Runs"

    def __str__(self) -> str:
        ts = self.generated_at.strftime("%Y-%m-%d %H:%M") if self.generated_at else "unsaved"
        return f"Report [{self.status}] @ {ts} (org={self.organization_id})"
