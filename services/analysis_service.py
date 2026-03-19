"""
AnalysisService — orchestrates analyzer runs end-to-end.

Calling run_analysis() will:
  1. Create an AnalysisRun record with status=PENDING so in-progress runs
     are visible immediately.
  2. Instantiate the requested Analyzer via AnalyzerFactory.
  3. Execute analyzer.run(organization_id).
  4. On success  → mark the run SUCCEEDED, persist results_summary.
  5. On failure  → mark the run FAILED, store the exception message.
  6. On success  → call AlertService to generate Alert objects from results.
  7. Write an ANALYSIS_RUN AuditLog entry recording the outcome.

The run status update is committed before alerts are generated so that a
failure inside AlertService never reverts a SUCCEEDED run back to PENDING.
"""

from __future__ import annotations

from uuid import UUID

from django.db import transaction

from apps.analytics.models import AnalysisRun
from apps.audit.models import AuditLog
from apps.transactions.models import Transaction
from factories.analyzer_factory import AnalyzerFactory
from services.alert_service import AlertService
from services.exceptions import AlreadyCurrentError


class AnalysisService:
    @staticmethod
    def run_analysis(
        organization_id: UUID | str,
        analysis_type: str,
    ) -> AnalysisRun:
        """
        Execute a named analyzer for the given organization.

        Parameters
        ----------
        organization_id : UUID | str
            PK of the Organization to analyse.
        analysis_type : str
            Must be a key registered in AnalyzerFactory (e.g. "large_transaction").

        Returns
        -------
        AnalysisRun
            The fully-updated AnalysisRun record (status=SUCCEEDED or FAILED).

        Raises
        ------
        ValueError
            Re-raised if AnalyzerFactory does not recognise *analysis_type*,
            so the caller (view) can return HTTP 400 without a 500 traceback.
        """
        # Validate the analyzer type early — before creating any DB record —
        # so an unknown type returns a clean 400, not a FAILED AnalysisRun.
        analyzer = AnalyzerFactory.create(analysis_type)  # raises ValueError if unknown

        # Guard: skip re-analysis if no new transactions have been imported since
        # the last successful run of this type.
        latest_tx = (
            Transaction.objects.filter(organization_id=organization_id)
            .order_by("-created_at")
            .values("created_at")
            .first()
        )
        if latest_tx is not None:
            last_succeeded = (
                AnalysisRun.objects.filter(
                    organization_id=organization_id,
                    analysis_type=analysis_type,
                    status=AnalysisRun.Status.SUCCEEDED,
                )
                .order_by("-run_time")
                .values("run_time")
                .first()
            )
            if last_succeeded and last_succeeded["run_time"] >= latest_tx["created_at"]:
                raise AlreadyCurrentError(analysis_type)

        with transaction.atomic():
            run = AnalysisRun.objects.create(
                organization_id=organization_id,
                analysis_type=analysis_type,
                # status defaults to PENDING; results_summary/error_message are NULL.
            )

        try:
            results = analyzer.run(organization_id)
        except Exception as exc:  # noqa: BLE001
            # Only store the exception message — avoid persisting potentially
            # sensitive frames (file paths, local variables) in the AuditLog.
            error_message = f"{type(exc).__name__}: {exc}"

            with transaction.atomic():
                run.status = AnalysisRun.Status.FAILED
                run.error_message = error_message
                run.full_clean()
                run.save(update_fields=["status", "error_message"])

                AuditLog.objects.create(
                    organization_id=organization_id,
                    event_type="ANALYSIS_RUN",
                    metadata={
                        "run_id": str(run.id),
                        "analysis_type": analysis_type,
                        "status": AnalysisRun.Status.FAILED,
                        "error": error_message,
                    },
                )

            return run

        # Commit the SUCCEEDED status before generating alerts — a failure in
        # AlertService must not roll back a run that has already completed.
        try:
            with transaction.atomic():
                run.status = AnalysisRun.Status.SUCCEEDED
                run.results_summary = results
                run.full_clean()
                run.save(update_fields=["status", "results_summary"])
        except Exception as exc:  # noqa: BLE001
            # full_clean() or save() failed; mark FAILED so the run is not
            # left stuck at PENDING. Open a fresh transaction — the one above
            # was rolled back when the exception was raised.
            error_message = f"{type(exc).__name__}: {exc}"
            with transaction.atomic():
                run.status = AnalysisRun.Status.FAILED
                run.error_message = error_message
                run.save(update_fields=["status", "error_message"])
                AuditLog.objects.create(
                    organization_id=organization_id,
                    event_type="ANALYSIS_RUN",
                    metadata={
                        "run_id": str(run.id),
                        "analysis_type": analysis_type,
                        "status": AnalysisRun.Status.FAILED,
                        "error": error_message,
                    },
                )
            raise

        try:
            alerts_created = AlertService.generate_alerts(organization_id, analysis_type, results)
            alert_error = None
        except Exception as exc:  # noqa: BLE001
            alerts_created = []
            alert_error = f"{type(exc).__name__}: {exc}"

        with transaction.atomic():
            metadata = {
                "run_id": str(run.id),
                "analysis_type": analysis_type,
                "status": AnalysisRun.Status.SUCCEEDED,
                "alerts_created": len(alerts_created),
            }
            if alert_error is not None:
                metadata["alert_failure"] = alert_error
            AuditLog.objects.create(
                organization_id=organization_id,
                event_type="ANALYSIS_RUN",
                metadata=metadata,
            )

        return run