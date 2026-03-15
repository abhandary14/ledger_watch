# Changelog

All notable changes to LedgerWatch are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.0.0] — 2026-03-15

Initial public release.

### Added

#### Core Infrastructure
- Django 5.x project scaffold with PostgreSQL via psycopg 3
- Docker + Docker Compose setup (API on port 8000, PostgreSQL on port 5433 locally)
- Environment-variable-driven configuration via `python-dotenv`
- `GET /health` liveness endpoint
- Gunicorn production server in Docker image
- `pytest` + `pytest-django` test configuration

#### Data Models
- `Organization` — multi-tenant root entity (UUID primary key)
- `Transaction` — financial transaction with decimal amount validation, vendor/date indexes
- `AnalysisRun` — persisted analysis results with PENDING/SUCCEEDED/FAILED state machine enforced at ORM and DB constraint level
- `Alert` — risk alert with LOW/MEDIUM/HIGH severity and OPEN/ACKNOWLEDGED/RESOLVED lifecycle
- `AuditLog` — write-once, immutable audit trail (raises `PermissionDenied` on update/delete)

#### Transaction API
- `POST /api/v1/transactions/import` — atomic bulk import with per-row validation and audit log
- `GET /api/v1/transactions/` — paginated list with `vendor`, `category`, `date_from`, `date_to` filters
- `GET /api/v1/transactions/{id}/` — single transaction retrieval

#### Analysis Engine
- `BaseAnalyzer` abstract interface for pluggable analyzers
- `AnalyzerFactory` implementing the Factory Method pattern with a runtime registry
- `LargeTransactionAnalyzer` — flags amounts exceeding 2× mean or a $10k floor
- `BurnRateAnalyzer` — monthly revenue vs. expenses with runway calculation
- `VendorSpikeAnalyzer` — month-over-month vendor spend comparison
- `DuplicateTransactionAnalyzer` — identical vendor+amount within 48-hour windows
- `POST /api/v1/analysis/run` — triggers a run, persists results, auto-generates alerts
- `GET /api/v1/analysis/results` — paginated list with `organization_id`, `analysis_type`, `status` filters
- `GET /api/v1/analysis/results/{id}/` — full run detail with `results_summary`

#### Alert System
- `AlertService` with severity mapping (HIGH/MEDIUM/LOW) per analyzer type
- `GET /api/v1/alerts/` — paginated list with `organization_id`, `alert_type`, `severity`, `status` filters
- `POST /api/v1/alerts/{id}/acknowledge` — OPEN → ACKNOWLEDGED state transition (409 if not OPEN)
- `POST /api/v1/alerts/{id}/resolve` — → RESOLVED state transition (409 if already RESOLVED)
- Audit log entry written on every state transition

#### Synthetic Data
- `python manage.py seed_transactions` management command (Faker-based)
- Generates ~270 transactions including anomalous large transactions, near-duplicates, vendor spikes, and revenue entries
- Supports `--count`, `--org`, `--clear` options

#### API Documentation
- `drf-spectacular` OpenAPI 3.0 schema generation
- Swagger UI at `/api/docs/`
- ReDoc at `/api/redoc/`
- Raw schema at `/api/schema/`
- `@extend_schema` decorators on all views with tags, summaries, and response codes

#### CI/CD
- Jenkinsfile pipeline: Lint → Test → Build Image → Run Migrations → Deploy
- Isolated PostgreSQL container per build (no shared state between builds)
- Jenkins credentials used for `SECRET_KEY` and `DB_PASSWORD`

#### Testing
- 9 test files covering all layers: models, analyzers, services, and API endpoints
- Multi-tenant isolation tested (org1 cannot see org2's data)
- Alert state machine transitions tested including conflict cases
- `AnalysisRun` status state machine and DB constraints tested
