import uuid

from django.db import models

from apps.organizations.models import Organization


class AnalysisRun(models.Model):
    """
    Audit record for a single execution of an Analyzer against an Organization.

    Each time ``AnalysisService.run_analysis()`` is called, one ``AnalysisRun``
    is persisted so that:
    - The caller can poll for results via the API.
    - Historical runs can be compared over time.
    - The raw output of any analyzer is always recoverable from the DB.

    ``results_summary`` stores the full JSON output returned by the analyzer's
    ``run()`` method — schema is analyzer-specific and intentionally untyped.
    """

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
    run_time = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the analysis was executed. Set automatically.",
    )
    results_summary = models.JSONField(
        help_text="Serialized output dict returned by the Analyzer's run() method.",
    )

    class Meta:
        ordering = ["-run_time"]
        verbose_name = "Analysis Run"
        verbose_name_plural = "Analysis Runs"

    def __str__(self) -> str:
        return f"{self.analysis_type} @ {self.run_time:%Y-%m-%d %H:%M} (org={self.organization_id})"
