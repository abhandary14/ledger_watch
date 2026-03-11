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

All DB state changes are wrapped in a single atomic block so the
AnalysisRun row is always consistent with the actual outcome.
"""

from __future__ import annotations

import traceback
from uuid import UUID

from django.db import transaction

from apps.analytics.models import AnalysisRun
from apps.audit.models import AuditLog
from factories.analyzer_factory import AnalyzerFactory
from services.alert_service import AlertService


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

        with transaction.atomic():
            run = AnalysisRun.objects.create(
                organization_id=organization_id,
                analysis_type=analysis_type,
                # status defaults to PENDING; results_summary/error_message are NULL.
            )

        alerts_created: list = []
        try:
            results = analyzer.run(organization_id)

            with transaction.atomic():
                run.status = AnalysisRun.Status.SUCCEEDED
                run.results_summary = results
                run.full_clean()
                run.save(update_fields=["status", "results_summary"])

                alerts_created = AlertService.generate_alerts(
                    organization_id, analysis_type, results
                )

                AuditLog.objects.create(
                    organization_id=organization_id,
                    event_type="ANALYSIS_RUN",
                    metadata={
                        "run_id": str(run.id),
                        "analysis_type": analysis_type,
                        "status": AnalysisRun.Status.SUCCEEDED,
                        "alerts_created": len(alerts_created),
                    },
                )

        except Exception as exc:  # noqa: BLE001
            # Capture the full traceback for debugging, but only store the
            # message in the DB to avoid storing potentially sensitive frames.
            error_message = f"{type(exc).__name__}: {exc}"
            tb_lines = traceback.format_exc()

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
                        # Store first 500 chars of traceback for quick triage.
                        "traceback_snippet": tb_lines[:500],
                    },
                )

        return run
