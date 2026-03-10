import uuid

from django.db import models

from apps.organizations.models import Organization


class AnalysisRun(models.Model):
    """
    Audit record for a single execution of an Analyzer against an Organization.

    Each time ``AnalysisService.run_analysis()`` is called, one ``AnalysisRun``
    is persisted immediately with ``status=PENDING`` so that in-progress runs
    are visible. The service then updates ``status``, ``results_summary``, or
    ``error_message`` once the analyzer completes or fails.

    Lifecycle:
        PENDING → SUCCEEDED  (normal path)
        PENDING → FAILED     (analyzer raised an exception)

    ``results_summary`` stores the full JSON output returned by the analyzer's
    ``run()`` method — schema is analyzer-specific and intentionally untyped.
    It is nullable so a PENDING or FAILED run can be persisted without results.
    ``error_message`` captures the exception detail on failure.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this analysis run (UUID v4, auto-generated).",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="analysis_runs",
        help_text="The organization this analysis was run against.",
    )
    analysis_type = models.CharField(
        max_length=100,
        help_text="Analyzer key used for this run (e.g. 'large_transaction').",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text=(
            "Lifecycle state of this run: PENDING (created, not yet complete), "
            "SUCCEEDED (analyzer finished normally), or FAILED (analyzer raised)."
        ),
    )
    run_time = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the analysis run record was created. Set automatically.",
    )
    results_summary = models.JSONField(
        null=True,
        blank=True,
        help_text=(
            "Serialized output dict returned by the Analyzer's run() method. "
            "Null while the run is PENDING or when the run FAILED before producing output."
        ),
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Exception detail captured when status=FAILED. "
            "Null for PENDING and SUCCEEDED runs."
        ),
    )

    class Meta:
        ordering = ["-run_time"]
        verbose_name = "Analysis Run"
        verbose_name_plural = "Analysis Runs"

    def __str__(self) -> str:
        # run_time is auto_now_add so it is None on unsaved instances.
        ts = self.run_time.strftime("%Y-%m-%d %H:%M") if self.run_time else "unsaved"
        return f"{self.analysis_type} [{self.status}] @ {ts} (org={self.organization_id})"
