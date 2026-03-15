import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.organizations.models import Organization


class Transaction(models.Model):
    """
    Represents a single financial transaction belonging to an Organization.

    Transactions are the core data ingested by LedgerWatch. They are analysed
    by the various Analyzer engines to surface risk signals and generate Alerts.

    Design notes:
    - UUID primary key avoids enumerable IDs in the API.
    - ``vendor`` and ``date`` carry ``db_index=True`` because both are used as
      filter predicates in every Analyzer query (TDD §15).
    - ``amount`` uses DecimalField (not FloatField) to prevent floating-point
      rounding errors in financial calculations.
    - ``description`` and ``category`` are optional — real imports may omit them.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this transaction (UUID v4, auto-generated).",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="transactions",
        help_text="The organization this transaction belongs to.",
    )
    date = models.DateField(
        db_index=True,
        help_text="Calendar date on which the transaction occurred.",
    )
    vendor = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Name of the vendor or counterparty (e.g. 'AWS', 'Stripe').",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Transaction amount in the organization's currency. Must be positive (> 0).",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional free-text description of the transaction.",
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional category label (e.g. 'SaaS', 'Payroll', 'Revenue').",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was inserted. Set automatically.",
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            # Composite index used by VendorSpikeAnalyzer and monthly aggregations.
            models.Index(fields=["organization", "date"], name="tx_org_date_idx"),
            # Composite index used by DuplicateTransactionAnalyzer.
            models.Index(fields=["vendor", "amount", "date"], name="tx_vendor_amount_date_idx"),
        ]
        constraints = [
            # DB-level guard — rejects negative/zero amounts even from raw SQL.
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="transaction_amount_positive",
            ),
        ]

    def clean(self) -> None:
        """ORM-level validation — catches saves via admin and model.full_clean()."""
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "Transaction amount must be greater than zero."})

    def __str__(self) -> str:
        return f"{self.date} | {self.vendor} | {self.amount}"
