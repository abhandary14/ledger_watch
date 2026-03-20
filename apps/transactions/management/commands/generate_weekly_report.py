"""
generate_weekly_report — Django management command to generate financial risk reports.

Runs the full report pipeline for one or all organizations that have unreported alerts.
Intended to be called from an OS-level cron job (e.g. every Friday at 18:00) or manually.

Usage:
    python manage.py generate_weekly_report
    python manage.py generate_weekly_report --org "Acme Corp"

Cron example (every Friday at 18:00):
    0 18 * * 5 cd /path/to/ledger_watch && python manage.py generate_weekly_report >> logs/weekly_report.log 2>&1
"""

from django.core.management.base import BaseCommand, CommandError

from apps.alerts.models import Alert
from apps.organizations.models import Organization
from services.report_service import ReportService


class Command(BaseCommand):
    help = "Generate weekly financial risk PDF reports for organizations with unreported alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            metavar="NAME",
            help="Generate a report for this organization only (exact name match).",
        )

    def handle(self, *args, **options):
        org_name = options.get("org")

        if org_name:
            orgs = self._get_named_org(org_name)
        else:
            orgs = self._orgs_with_unreported_alerts()

        if not orgs:
            self.stdout.write("No organizations with unreported alerts found.")
            return

        for org in orgs:
            self._run_for_org(org)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_named_org(self, name: str):
        try:
            org = Organization.objects.get(name=name)
        except Organization.DoesNotExist:
            raise CommandError(f"Organization '{name}' not found.")
        return [org]

    def _orgs_with_unreported_alerts(self):
        org_ids = (
            Alert.objects.filter(reported=False)
            .values_list("organization_id", flat=True)
            .distinct()
        )
        return list(Organization.objects.filter(pk__in=org_ids))

    def _run_for_org(self, org: Organization) -> None:
        label = f"[{org.name}]"
        try:
            report_run = ReportService.generate_report(
                organization_id=org.id,
                triggered_by="scheduled",
            )
        except Exception as exc:
            self.stderr.write(f"{label} ERROR: {exc}")
            return

        if report_run is None:
            self.stdout.write(f"{label} Skipped — no new alerts since last report.")
        else:
            self.stdout.write(
                self.style.SUCCESS(f"{label} Report saved: {report_run.report_path}")
            )
