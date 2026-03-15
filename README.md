# LedgerWatch

A Django REST Framework backend for financial transaction analysis and risk monitoring.
LedgerWatch ingests synthetic business transactions, runs pluggable analysis engines, and generates severity-ranked alerts — all scoped to multi-tenant organizations.

![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-5.x-green)
![DRF](https://img.shields.io/badge/djangorestframework-3.15-red)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## The frontend is in progress.

## Features

- **Bulk transaction import** with full validation and atomic writes
- **Pluggable analysis engines** — large transactions, burn rate, vendor spikes, duplicates
- **Automatic alert generation** with severity mapping (LOW / MEDIUM / HIGH)
- **Alert lifecycle** — OPEN → ACKNOWLEDGED → RESOLVED with audit trail
- **Write-once audit log** for every significant action
- **Interactive API docs** via Swagger UI and ReDoc (drf-spectacular)
- **Docker + PostgreSQL** — single-command local setup
- **Jenkins CI/CD** — lint, test, build, deploy pipeline

---

## Architecture

```
HTTP Request
    │
    ▼
View  (HTTP parsing only — no business logic)
    │
    ▼
Service  (orchestration, atomic DB transactions)
    │
    ├─► Analyzer  (pluggable; returns plain dict)
    │       └── AnalyzerFactory (Factory Method pattern)
    │
    ├─► AlertService  (dict → Alert objects with severity)
    │
    ├─► Model  (ORM clean() + DB CheckConstraints)
    │
    └─► AuditLog  (write-once, immutable)
```

### Analysis Engines

| Key | What it detects |
|-----|----------------|
| `large_transaction` | Amounts > 5× mean (HIGH) or > 2× mean / $10k floor (MEDIUM) |
| `burn_rate` | Monthly cash runway — < 3 months (HIGH), 3–6 months (MEDIUM) |
| `vendor_spike` | Month-over-month vendor spend — ≥ 50% increase (MEDIUM), 25–50% or new vendor (LOW) |
| `duplicate` | Identical vendor + amount within a 48-hour window (LOW) |

---

## Quick Start

### With Docker (recommended)

```bash
git clone https://github.com/abhandary14/ledger-watch.git
cd ledger-watch

cp config/.env.example config/.env   # edit credentials if needed
docker compose up --build
```

The API will be available at `http://localhost:8000`.

### Without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config/.env.example config/.env   # point DB_HOST=localhost
python manage.py migrate
python manage.py runserver
```

---

## API Documentation

| Interface | URL |
|-----------|-----|
| Swagger UI | `http://localhost:8000/api/docs/` |
| ReDoc | `http://localhost:8000/api/redoc/` |
| Raw OpenAPI schema | `http://localhost:8000/api/schema/` |

---

## API Reference

All endpoints are under `/api/v1/`.

### Transactions

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/transactions/import` | Bulk-import transactions. Body: `{organization_id, transactions: [...]}` |
| `GET` | `/transactions/` | List transactions. Filters: `vendor`, `category`, `date_from`, `date_to` |
| `GET` | `/transactions/{id}/` | Retrieve single transaction |

**Import request body:**
```json
{
  "organization_id": "uuid",
  "transactions": [
    {
      "date": "2025-11-01",
      "vendor": "AWS",
      "amount": "4200.00",
      "category": "Infrastructure",
      "description": "Monthly compute"
    }
  ]
}
```

### Analysis

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analysis/run` | Trigger an analysis run |
| `GET` | `/analysis/results` | List runs. Filters: `organization_id`, `analysis_type`, `status` |
| `GET` | `/analysis/results/{id}/` | Retrieve single run with full `results_summary` |

**Run request body:**
```json
{
  "organization_id": "uuid",
  "analysis_type": "large_transaction"
}
```

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/alerts/` | List alerts. Filters: `organization_id`, `alert_type`, `severity`, `status` |
| `POST` | `/alerts/{id}/acknowledge` | OPEN → ACKNOWLEDGED. Returns 409 if not OPEN |
| `POST` | `/alerts/{id}/resolve` | → RESOLVED. Returns 409 if already RESOLVED |

---

## Seed Data

```bash
python manage.py seed_transactions                        # ~270 synthetic transactions
python manage.py seed_transactions --count 100 --clear   # wipe first, then seed
python manage.py seed_transactions --org "My Org"        # seed into named org
```

Seeded data includes anomalous large transactions, near-duplicate pairs, vendor spikes, and revenue entries — designed to trigger all four analysis engines.

---

## Running Tests

```bash
pytest                                                          # all tests
pytest tests/test_health.py                                    # single file
pytest tests/test_health.py::TestHealth::test_health_check    # single test
```

The test suite covers models, all four analyzers, both services, and every API endpoint.

---

## Linting

```bash
ruff check .
ruff format .
```

---

## Environment Variables

Copy `config/.env.example` to `config/.env` and adjust as needed:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(required)* | Django secret key |
| `DEBUG` | `True` | Set `False` in production |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated |
| `DB_NAME` | `ledgerwatch` | PostgreSQL database name |
| `DB_USER` | `ledger` | Database user |
| `DB_PASSWORD` | `ledger` | Database password |
| `DB_HOST` | `postgres` | Hostname (use `localhost` outside Docker) |
| `DB_PORT` | `5432` | PostgreSQL port |

---

## CI/CD

The `Jenkinsfile` defines a pipeline with the following stages:

1. **Lint** — `ruff check .`
2. **Test** — `pytest --tb=short` against an isolated PostgreSQL container
3. **Build Image** — `docker build -t ledgerwatch:<build>`
4. **Run Migrations** — `python manage.py migrate`
5. **Deploy** — `docker compose up -d`

Credentials (`SECRET_KEY`, `DB_PASSWORD`) are injected as Jenkins secret text credentials.

---

## Project Structure

```
ledger_watch/
├── apps/
│   ├── organizations/   # Organization model (multi-tenant scoping)
│   ├── transactions/    # Transaction model, import API, seed command
│   ├── analytics/       # AnalysisRun model, analysis API
│   ├── alerts/          # Alert model, acknowledge/resolve API
│   └── audit/           # AuditLog (write-once)
├── services/
│   ├── analyzers/       # BaseAnalyzer + 4 concrete analyzers
│   ├── analysis_service.py
│   ├── alert_service.py
│   └── transaction_service.py
├── factories/
│   └── analyzer_factory.py   # Factory Method pattern
├── ledgerwatch/         # Django project config (settings, urls)
├── tests/               # pytest test suite
├── config/              # .env.example
├── docker/              # Dockerfile
├── docs/                # PRD.md, TDD.md
├── docker-compose.yml
├── Jenkinsfile
└── requirements.txt
```

---

## License

MIT — see [LICENSE](LICENSE).
