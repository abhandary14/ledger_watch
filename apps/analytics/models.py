import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

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

    Enforced field invariants (validated at ORM and DB level):
    - PENDING   → results_summary IS NULL,     error_message IS NULL
    - SUCCEEDED → results_summary IS NOT NULL,  error_message IS NULL
    - FAILED    → results_summary IS NULL,      error_message IS NOT NULL

    ``status`` is the single source of truth; contradictory combinations
    are rejected by ``clean()`` (ORM/admin/DRF) and by ``CheckConstraint``
    (raw SQL / bulk inserts).
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
            "Must be NULL for PENDING and FAILED runs; must be set for SUCCEEDED runs."
        ),
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text=(
            "Exception detail captured when status=FAILED. "
            "Must be NULL for PENDING and SUCCEEDED runs; must be set for FAILED runs."
        ),
    )

    class Meta:
        ordering = ["-run_time"]
        verbose_name = "Analysis Run"
        verbose_name_plural = "Analysis Runs"
        constraints = [
            # PENDING: no results, no error.
            models.CheckConstraint(
                check=(
                    ~Q(status="PENDING")
                    | Q(results_summary__isnull=True, error_message__isnull=True)
                ),
                name="analysisrun_pending_fields_null",
            ),
            # SUCCEEDED: results required, no error.
            models.CheckConstraint(
                check=(
                    ~Q(status="SUCCEEDED")
                    | Q(results_summary__isnull=False, error_message__isnull=True)
                ),
                name="analysisrun_succeeded_has_results_no_error",
            ),
            # FAILED: error required, no results.
            models.CheckConstraint(
                check=(
                    ~Q(status="FAILED")
                    | Q(error_message__isnull=False, results_summary__isnull=True)
                ),
                name="analysisrun_failed_has_error_no_results",
            ),
        ]

    def clean(self) -> None:
        """
        Enforce status/field invariants at the ORM level.

        Called by full_clean(), Django admin saves, and DRF serializers that
        invoke validate(). Also the right place for services to call explicitly
        before saving a terminal state.
        """
        super().clean()
        errors = {}

        if self.status == self.Status.PENDING:
            if self.results_summary is not None:
                errors["results_summary"] = (
                    "results_summary must be null while the run is PENDING."
                )
            if self.error_message:
                errors["error_message"] = (
                    "error_message must be null while the run is PENDING."
                )

        elif self.status == self.Status.SUCCEEDED:
            if self.results_summary is None:
                errors["results_summary"] = (
                    "results_summary is required when the run SUCCEEDED."
                )
            if self.error_message:
                errors["error_message"] = (
                    "error_message must be null for a SUCCEEDED run."
                )

        elif self.status == self.Status.FAILED:
            if not self.error_message:
                errors["error_message"] = (
                    "error_message is required when the run FAILED."
                )
            if self.results_summary is not None:
                errors["results_summary"] = (
                    "results_summary must be null for a FAILED run."
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        # run_time is auto_now_add so it is None on unsaved instances.
        ts = self.run_time.strftime("%Y-%m-%d %H:%M") if self.run_time else "unsaved"
        return f"{self.analysis_type} [{self.status}] @ {ts} (org={self.organization_id})"
