"""
Django settings for ledgerwatch project.
All sensitive values are loaded from environment variables (see config/.env.example).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if it exists (local development convenience)
load_dotenv(BASE_DIR / "config" / ".env")

# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    # Local apps (registered in Phase 2)
    "apps.organizations",
    "apps.transactions",
    "apps.analytics",
    "apps.alerts",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ledgerwatch.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ledgerwatch.wsgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL, all credentials from env
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "ledgerwatch"),
        "USER": os.getenv("DB_USER", "ledger"),
        "PASSWORD": os.getenv("DB_PASSWORD", "ledger"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"

# ---------------------------------------------------------------------------
# Default primary key — overridden per-model with UUIDField
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "LedgerWatch API",
    "DESCRIPTION": (
        "LedgerWatch is a Django REST Framework backend for financial transaction analysis "
        "and risk monitoring. It ingests synthetic business transactions, runs pluggable "
        "analysis engines (large transactions, burn rate, vendor spikes, duplicates), and "
        "generates severity-ranked alerts.\n\n"
        "All data is scoped to an **Organization** (multi-tenant). Pass `organization_id` "
        "explicitly in request bodies — there is no JWT authentication in the MVP.\n\n"
        "**Docs:** `/api/docs/` (Swagger UI) · `/api/redoc/` (ReDoc) · `/api/schema/` (raw YAML)"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "Health", "description": "Service liveness check."},
        {
            "name": "Transactions",
            "description": "Bulk-import and query financial transactions.",
        },
        {
            "name": "Analysis",
            "description": (
                "Trigger and inspect analysis runs. "
                "Available analyzers: `large_transaction`, `burn_rate`, "
                "`vendor_spike`, `duplicate`."
            ),
        },
        {
            "name": "Alerts",
            "description": (
                "View risk alerts generated by analysis runs. "
                "Alerts follow the state machine: **OPEN → ACKNOWLEDGED → RESOLVED**."
            ),
        },
    ],
    "CONTACT": {
        "name": "LedgerWatch",
        "url": "https://github.com/abhandary14/ledger-watch",
    },
    "LICENSE": {"name": "MIT"},
}
