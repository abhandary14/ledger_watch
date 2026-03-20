"""
ReportService — orchestrates the AI-assisted weekly report pipeline.

Pipeline:
  1. Run all four analysis types (skips types already current via AlreadyCurrentError).
  2. Fetch unreported alerts for the org.
  3. If none → return None (caller receives "no new alerts").
  4. Build compact JSON payload for Claude.
  5. Call Claude API → receive HTML narrative as JSON.
  6. Render PDF (HTML → PDF via xhtml2pdf).
  7. Write PDF to REPORT_OUTPUT_DIR / filename.
  8. On successful write → mark alerts as reported=True.
  9. Create ReportRun (SUCCEEDED) + REPORT_GENERATED AuditLog entry.
  10. Return ReportRun.

On any exception in steps 5-7:
  - Create ReportRun (FAILED, error_message).
  - Re-raise so the caller (view or management command) can surface it.
  - reported flags are never set on failure.
"""

from __future__ import annotations

import html as _html
import json
import logging
import re
import traceback
from collections import defaultdict
from datetime import date
from pathlib import Path
from uuid import UUID

_logger = logging.getLogger(__name__)

import bleach

import anthropic
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from apps.alerts.models import Alert
from apps.analytics.models import AnalysisRun
from apps.audit.models import AuditLog
from apps.organizations.models import Organization
from apps.reports.models import ReportRun
from factories.analyzer_factory import AnalyzerFactory
from services.analysis_service import AnalysisService
from services.exceptions import AlreadyCurrentError

# Tags and attributes Claude is instructed to emit; everything else is stripped.
_NARRATIVE_ALLOWED_TAGS = ["h2", "h3", "p", "ul", "ol", "li", "strong", "em", "b", "i", "span", "br"]
_NARRATIVE_ALLOWED_ATTRS: dict = {"*": ["style"]}

_SYSTEM_PROMPT = (
    "You are a financial risk analyst generating a weekly monitoring report for a small business.\n"
    "You will receive a structured JSON summary of financial alerts detected by LedgerWatch.\n\n"
    "Return ONLY a valid JSON object in exactly this format:\n"
    '{"html": "<your HTML here>"}\n\n'
    "The html value must be valid HTML body content (no <html>, <head>, or <body> tags) "
    "with inline CSS, containing these three sections in order:\n"
    "1. Executive Summary — <h2>Executive Summary</h2> followed by 2-3 sentences in a <p> tag\n"
    "2. Key Findings — <h2>Key Findings</h2> then one <h3> + <p> per alert type that has alerts "
    "(skip types with zero alerts)\n"
    "3. Recommendations — <h2>Recommendations</h2> followed by a <ul> with 3-5 <li> items\n\n"
    "Use only inline CSS. Write in plain language for a non-technical business owner.\n"
    "Do not invent data not present in the input. Do not make specific financial predictions.\n"
    "Return nothing outside the JSON object — no markdown fences, no preamble."
)


class ReportService:
    @staticmethod
    def generate_report(
        organization_id: UUID | str,
        triggered_by: str = "manual",
    ) -> ReportRun | None:
        """
        Generate a PDF financial risk report for the given organization.

        Returns the created ReportRun on success, or None if there are no
        unreported alerts (no report generated, no ReportRun created).

        Raises ImproperlyConfigured if ANTHROPIC_API_KEY is not set.
        Raises and creates a FAILED ReportRun for any other exception.
        """
        if not settings.ANTHROPIC_API_KEY:
            raise ImproperlyConfigured(
                "ANTHROPIC_API_KEY is not configured. "
                "Set it in config/.env before generating reports."
            )

        # Run all four analyses; silently skip already-current types.
        # If any run fails, abort and create a FAILED ReportRun immediately.
        failed_types: list[str] = []
        for analysis_type in AnalyzerFactory.available():
            try:
                run = AnalysisService.run_analysis(organization_id, analysis_type)
            except AlreadyCurrentError:
                continue
            if run.status == AnalysisRun.Status.FAILED:
                failed_types.append(analysis_type)

        if failed_types:
            error_msg = f"Analysis failed for type(s): {', '.join(failed_types)}"
            report_run = ReportRun.objects.create(
                organization_id=organization_id,
                alert_count=0,
                triggered_by=triggered_by,
                status=ReportRun.Status.FAILED,
                error_message=error_msg,
            )
            AuditLog.objects.create(
                organization_id=organization_id,
                event_type="REPORT_GENERATED",
                metadata={
                    "report_run_id": str(report_run.id),
                    "triggered_by": triggered_by,
                    "status": ReportRun.Status.FAILED,
                    "failed_analysis_types": failed_types,
                },
            )
            raise RuntimeError(error_msg)

        # Create a PENDING ReportRun immediately to serve as a durable claim token.
        # This record is updated in-place to SUCCEEDED or FAILED; it is never left PENDING.
        report_run = ReportRun.objects.create(
            organization_id=organization_id,
            triggered_by=triggered_by,
            status=ReportRun.Status.PENDING,
        )

        # Atomically claim all unreported, unclaimed alerts for this run.
        # The WHERE report_run__isnull=True guard means each alert is claimed by
        # exactly one ReportRun even under concurrent calls.
        with transaction.atomic():
            claimed_count = Alert.objects.filter(
                organization_id=organization_id,
                reported=False,
                report_run__isnull=True,
            ).update(report_run_id=report_run.id)

        if claimed_count == 0:
            report_run.delete()
            return None

        alerts = list(
            Alert.objects.filter(report_run_id=report_run.id).order_by("created_at")
        )

        org = Organization.objects.get(pk=organization_id)

        try:
            payload = ReportService._build_payload(org, alerts, organization_id)
            narrative_html = ReportService._call_claude(payload)

            output_dir = Path(settings.REPORT_OUTPUT_DIR)
            output_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = ReportService._unique_path(output_dir, org.name, date.today(), report_run.id)
            ReportService._render_pdf(pdf_path, org.name, date.today(), alerts, narrative_html)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            _logger.exception("Report generation failed for org %s run %s", organization_id, report_run.id)
            ReportService._fail_run(report_run, organization_id, triggered_by, len(alerts), error_msg)
            raise

        try:
            relative_path = str(pdf_path.relative_to(Path(settings.BASE_DIR)))
        except ValueError:
            relative_path = str(pdf_path)

        try:
            with transaction.atomic():
                Alert.objects.filter(report_run_id=report_run.id).update(reported=True)
                report_run.status = ReportRun.Status.SUCCEEDED
                report_run.report_path = relative_path
                report_run.alert_count = len(alerts)
                report_run.save(update_fields=["status", "report_path", "alert_count"])
                AuditLog.objects.create(
                    organization_id=organization_id,
                    event_type="REPORT_GENERATED",
                    metadata={
                        "report_run_id": str(report_run.id),
                        "triggered_by": triggered_by,
                        "alert_count": len(alerts),
                        "report_path": relative_path,
                        "status": ReportRun.Status.SUCCEEDED,
                    },
                )
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            _logger.exception("Failed to commit report run %s for org %s", report_run.id, organization_id)
            ReportService._fail_run(report_run, organization_id, triggered_by, len(alerts), error_msg)
            raise

        return report_run

    # ------------------------------------------------------------------
    # Payload builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_payload(org: Organization, alerts: list, organization_id) -> dict:
        """Build the compact JSON summary sent to Claude."""
        by_severity: dict[str, int] = defaultdict(int)
        by_type: dict[str, int] = defaultdict(int)
        by_status: dict[str, int] = defaultdict(int)

        for alert in alerts:
            by_severity[alert.severity] += 1
            by_type[alert.alert_type] += 1
            by_status[alert.status] += 1

        period_start = alerts[0].created_at.date().isoformat() if alerts else date.today().isoformat()

        return {
            "organization": org.name,
            "report_date": date.today().isoformat(),
            "period": f"alerts since {period_start}",
            "alert_counts": {
                "total": len(alerts),
                "by_severity": dict(by_severity),
                "by_type": dict(by_type),
                "by_status": dict(by_status),
            },
            "findings": ReportService._build_findings(organization_id, dict(by_type)),
        }

    @staticmethod
    def _build_findings(organization_id, type_counts: dict) -> dict:
        """
        Extract structured findings per alert type from the most recent
        SUCCEEDED AnalysisRun results_summary for each type.
        """
        findings = {}
        for alert_type, count in type_counts.items():
            finding: dict = {"count": count}

            run = (
                AnalysisRun.objects.filter(
                    organization_id=organization_id,
                    analysis_type=alert_type,
                    status=AnalysisRun.Status.SUCCEEDED,
                )
                .order_by("-run_time")
                .first()
            )
            if run and run.results_summary:
                rs = run.results_summary
                if alert_type == "large_transaction":
                    txs = rs.get("flagged_transactions", [])
                    if txs:
                        finding["max_amount"] = max(float(tx.get("amount", 0)) for tx in txs)
                        finding["vendors"] = [tx.get("vendor", "") for tx in txs]
                elif alert_type == "burn_rate":
                    runway = rs.get("runway_months")
                    finding["runway_months"] = float(runway) if runway is not None else None
                    finding["net_burn"] = float(rs.get("net_burn", rs.get("net_monthly_burn", 0)))
                elif alert_type == "vendor_spike":
                    finding["vendors"] = [
                        {
                            "vendor": v.get("vendor"),
                            "percent_increase": float(v["increase_pct"]) if v.get("increase_pct") is not None else None,
                        }
                        for v in rs.get("flagged_vendors", [])
                    ]
                elif alert_type == "duplicate":
                    finding["pairs"] = [
                        {"vendor": g.get("vendor"), "amount": g.get("amount")}
                        for g in rs.get("duplicate_groups", [])
                    ]

            findings[alert_type] = finding
        return findings

    # ------------------------------------------------------------------
    # Claude API call
    # ------------------------------------------------------------------

    @staticmethod
    def _call_claude(payload: dict) -> str:
        """Send the payload to Claude and return the narrative HTML string."""
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        user_message = (
            "Analyse the following alert data and generate the report:\n\n"
            + json.dumps(payload, indent=2)
        )
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        if not message.content or not hasattr(message.content[0], "text"):
            raise ValueError(
                f"Claude returned an empty or unexpected response shape: {message.content!r}"
            )
        raw = message.content[0].text.strip()
        # Strip markdown code fences that Claude occasionally adds despite instructions.
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw).strip()
        try:
            data = json.loads(raw)
            return data["html"]
        except (json.JSONDecodeError, KeyError) as exc:
            raise ValueError(
                f"Claude returned unexpected format: {exc}\nRaw response: {raw[:300]}"
            ) from exc

    # ------------------------------------------------------------------
    # PDF rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _render_pdf(
        path: Path,
        org_name: str,
        report_date: date,
        alerts: list,
        narrative_html: str,
    ) -> None:
        """Build a complete HTML document and convert it to PDF via xhtml2pdf."""
        from xhtml2pdf import pisa

        # Sanitize owner-controlled and AI-generated content before interpolation.
        safe_org_name = _html.escape(org_name)
        safe_narrative = bleach.clean(
            narrative_html,
            tags=_NARRATIVE_ALLOWED_TAGS,
            attributes=_NARRATIVE_ALLOWED_ATTRS,
            strip=True,
            strip_comments=True,
        )

        severities = ["HIGH", "MEDIUM", "LOW"]
        statuses = ["OPEN", "ACKNOWLEDGED", "RESOLVED"]

        counts: dict[tuple, int] = defaultdict(int)
        for alert in alerts:
            counts[(alert.severity, alert.status)] += 1

        stats_rows = "".join(
            "<tr><td><strong>{sev}</strong></td>{cells}</tr>".format(
                sev=sev,
                cells="".join(
                    f"<td style='text-align:center;'>{counts.get((sev, st), 0)}</td>"
                    for st in statuses
                ),
            )
            for sev in severities
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11px;
    color: #333333;
    margin: 40px;
  }}
  h1 {{
    font-size: 22px;
    color: #1a1a2e;
    margin: 0 0 4px 0;
  }}
  .subtitle {{
    color: #666666;
    font-size: 11px;
    margin: 2px 0;
  }}
  hr {{
    border: none;
    border-top: 1px solid #dddddd;
    margin: 16px 0;
  }}
  h2 {{
    font-size: 13px;
    font-weight: bold;
    color: #1a1a2e;
    text-transform: uppercase;
    margin-top: 20px;
    margin-bottom: 6px;
    padding-bottom: 4px;
    border-bottom: 1px solid #dddddd;
  }}
  h3 {{
    font-size: 11px;
    font-weight: bold;
    margin-top: 12px;
    margin-bottom: 4px;
  }}
  p {{
    margin: 0 0 8px 0;
    line-height: 1.5;
  }}
  ul {{
    margin: 4px 0;
    padding-left: 20px;
  }}
  li {{
    margin-bottom: 4px;
    line-height: 1.5;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
  }}
  th {{
    background-color: #1a1a2e;
    color: #ffffff;
    padding: 6px 10px;
    text-align: left;
    font-size: 10px;
  }}
  td {{
    padding: 5px 10px;
    border-bottom: 1px solid #eeeeee;
    font-size: 10px;
  }}
  tr:nth-child(even) td {{
    background-color: #f9f9f9;
  }}
</style>
</head>
<body>
  <h1>LedgerWatch</h1>
  <p class="subtitle">Weekly Financial Risk Report</p>
  <p class="subtitle">Organization: {safe_org_name}</p>
  <p class="subtitle">Generated: {report_date.strftime('%A, %d %B %Y')}</p>
  <hr/>
  <h2>Alert Statistics</h2>
  <table>
    <tr>
      <th>Severity</th>
      <th>Open</th>
      <th>Acknowledged</th>
      <th>Resolved</th>
    </tr>
    {stats_rows}
  </table>
  <hr/>
  {safe_narrative}
</body>
</html>"""

        with open(path, "wb") as f:
            result = pisa.CreatePDF(html, dest=f)

        if result.err:
            raise RuntimeError(f"PDF generation failed with {result.err} error(s).")

    # ------------------------------------------------------------------
    # File naming helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fail_run(
        report_run: ReportRun,
        organization_id,
        triggered_by: str,
        alert_count: int,
        error_msg: str,
    ) -> None:
        """
        Unclaim alerts and mark the ReportRun as FAILED.

        Called from both the Claude/PDF failure path and the success-commit
        failure path so cleanup is always consistent.
        """
        with transaction.atomic():
            Alert.objects.filter(report_run_id=report_run.id).update(report_run_id=None)
            report_run.status = ReportRun.Status.FAILED
            report_run.error_message = error_msg
            report_run.save(update_fields=["status", "error_message"])
            AuditLog.objects.create(
                organization_id=organization_id,
                event_type="REPORT_GENERATED",
                metadata={
                    "report_run_id": str(report_run.id),
                    "triggered_by": triggered_by,
                    "alert_count": alert_count,
                    "status": ReportRun.Status.FAILED,
                },
            )

    @staticmethod
    def _slugify(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

    @staticmethod
    def _unique_path(output_dir: Path, org_name: str, report_date: date, run_id) -> Path:
        """
        Return a deterministic path for this report run.

        Embeds a short token derived from run_id so the filename is unique
        per run without any filesystem check or counter loop.
        """
        slug = ReportService._slugify(org_name)
        short_id = str(run_id).replace("-", "")[:12]
        return output_dir / f"{slug}_{report_date.isoformat()}_{short_id}.pdf"
