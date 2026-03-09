# LedgerWatch — Technical Design Document (TDD)

## 1. Purpose

This document describes the technical architecture and implementation plan for LedgerWatch. It outlines system components, data models, APIs, services, and infrastructure required to implement the product defined in the PRD.

This project is designed to be fully open-source and deployable locally using Docker.

---

## 2. High-Level Architecture

```
Client (Postman / UI)
        |
REST API (Django REST Framework)
        |
Service Layer
        |
Analysis Engines
        |
PostgreSQL Database
```

Components:

* Django REST API
* Service Layer
* Analysis Engine modules
* PostgreSQL database
* Jenkins CI/CD pipeline
* Docker container environment

---

## 3. Technology Stack

Backend:

* Python 3
* Django
* Django REST Framework

Database:

* PostgreSQL

Infrastructure:

* Docker
* Docker Compose

CI/CD:

* Jenkins

Development Tools:

* VS Code
* Postman

---

## 4. Project Structure

```
ledgerwatch/
│
├── apps/
│   ├── organizations/
│   ├── transactions/
│   ├── analytics/
│   ├── alerts/
│   └── audit/
│
├── services/
│   ├── analyzers/
│   └── alert_service.py
│
├── factories/
│   └── analyzer_factory.py
│
├── management/
│   └── commands/
│       └── seed_transactions.py
│
├── config/
│
├── docker/
│
├── tests/
│
└── Jenkinsfile
```

---

## 5. Database Design

### organizations

| Field      | Type      | Description          |
| ---------- | --------- | -------------------- |
| id         | UUID      | Primary key          |
| name       | string    | Organization name    |
| created_at | timestamp | Record creation time |

### transactions

| Field           | Type      | Description             |
| --------------- | --------- | ----------------------- |
| id              | UUID      | Transaction ID          |
| organization_id | UUID      | Foreign key             |
| date            | date      | Transaction date        |
| vendor          | string    | Vendor name             |
| amount          | decimal   | Transaction amount      |
| description     | text      | Transaction description |
| category        | string    | Optional category       |
| created_at      | timestamp | Creation time           |

### alerts

| Field           | Type      | Description                    |
| --------------- | --------- | ------------------------------ |
| id              | UUID      | Alert ID                       |
| organization_id | UUID      | Related organization           |
| alert_type      | string    | Type of alert                  |
| severity        | string    | LOW / MEDIUM / HIGH            |
| message         | text      | Alert description              |
| status          | string    | OPEN / ACKNOWLEDGED / RESOLVED |
| created_at      | timestamp | Alert creation                 |

### analysis_runs

| Field           | Type      | Description      |
| --------------- | --------- | ---------------- |
| id              | UUID      | Run identifier   |
| organization_id | UUID      | Organization     |
| analysis_type   | string    | Type of analysis |
| run_time        | timestamp | Execution time   |
| results_summary | json      | Summary output   |

### audit_logs

| Field      | Type      | Description       |
| ---------- | --------- | ----------------- |
| id         | UUID      | Log ID            |
| event_type | string    | Event description |
| metadata   | json      | Event data        |
| created_at | timestamp | Event timestamp   |

---

## 6. API Design

### Transactions

Import transactions:

```
POST /transactions/import
```

Request body:

```
{
  "transactions": [
    {
      "vendor": "AWS",
      "amount": 250.00,
      "date": "2025-01-01",
      "description": "cloud infrastructure"
    }
  ]
}
```

List transactions:

```
GET /transactions
```

Retrieve transaction:

```
GET /transactions/{id}
```

---

### Analysis

Run analysis:

```
POST /analysis/run
```

Example request:

```
{
  "analysis_type": "burn_rate"
}
```

Get results:

```
GET /analysis/results
```

---

### Alerts

Retrieve alerts:

```
GET /alerts
```

Acknowledge alert:

```
POST /alerts/{id}/acknowledge
```

Resolve alert:

```
POST /alerts/{id}/resolve
```

---

### Health Check

```
GET /health
```

---

## 7. Analysis Engine Design

LedgerWatch uses modular analysis engines.

Each engine implements a common interface.

Example interface:

```
class Analyzer:
    def run(self, organization_id):
        pass
```

Example analyzers:

* BurnRateAnalyzer
* VendorSpikeAnalyzer
* DuplicateTransactionAnalyzer
* AnomalyAnalyzer

---

## 8. Factory Method Pattern

The Factory Method pattern is used to create analyzer instances.

Example:

```
class AnalyzerFactory:

    @staticmethod
    def create(analyzer_type):
        if analyzer_type == "burn_rate":
            return BurnRateAnalyzer()
        if analyzer_type == "vendor_spike":
            return VendorSpikeAnalyzer()
        if analyzer_type == "duplicate":
            return DuplicateTransactionAnalyzer()

        raise ValueError("Unknown analyzer")
```

This allows new analyzers to be added without changing service logic.

---

## 9. Service Layer

Services contain application business logic.

Example:

```
class AnalysisService:

    def run_analysis(self, organization_id, analysis_type):

        analyzer = AnalyzerFactory.create(analysis_type)

        results = analyzer.run(organization_id)

        return results
```

Alert generation logic is handled by `AlertService`.

---

## 10. Synthetic Data Generator

Synthetic data is generated using a Django management command.

Command:

```
python manage.py seed_transactions
```

The generator produces:

* recurring vendor payments
* customer revenue
* subscription expenses
* anomalies
* duplicate transactions

This ensures the project remains safe for public GitHub hosting.

---

## 11. Docker Setup

The project runs using Docker.

Services include:

* Django API
* PostgreSQL

Example docker-compose services:

```
api
postgres
```

Docker ensures consistent environments across systems.

---

## 12. Jenkins CI/CD Pipeline

Jenkins will automate testing and builds.

Pipeline stages:

```
1. Checkout code
2. Install dependencies
3. Run linting
4. Run tests
5. Build Docker image
6. Run migrations
7. Deploy container
```

Pipeline defined in:

```
Jenkinsfile
```

---

## 13. Testing Strategy

Testing will include:

Unit tests:

* analyzer logic
* service methods

Integration tests:

* API endpoints
* database interactions

Tools:

* pytest
* pytest-django

---

## 14. Security Considerations

Security practices include:

* environment variables for secrets
* no credentials stored in source code
* Docker-based deployment
* input validation

LedgerWatch will never process real financial data.

---

## 15. Performance Considerations

Initial MVP targets small datasets.

Potential optimizations:

* indexing transaction dates
* indexing vendor names
* pagination for API endpoints

---

## 16. Future Enhancements

Possible improvements:

* scheduled analysis jobs
* dashboard UI
* advanced anomaly detection models
* webhook alerts
* multi-organization support

---

## 17. Deployment

LedgerWatch can run locally using:

```
docker-compose up
```

This starts:

* PostgreSQL
* Django API

CI/CD pipelines automate builds and testing.

---

## 18. Open Source Compliance

The repository will include:

```
README.md
PRD.md
TDD.md
LICENSE
Dockerfile
docker-compose.yml
Jenkinsfile
requirements.txt
```

No proprietary datasets or private APIs will be included.

The project will be fully reproducible from GitHub.
