import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Organization(models.Model):
    """
    Represents a business entity using LedgerWatch.

    Every Transaction, Alert, and AnalysisRun is scoped to an Organization.
    This is the top-level tenant in the system.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the organization (UUID v4, auto-generated).",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name of the organization (e.g. 'Acme Corp').",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the organization record was created. Set automatically.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self) -> str:
        return self.name


class SecurityChallenge(models.Model):
    """
    Single-use security challenge token for destructive owner actions.

    One row per pending challenge (one per user at a time due to the
    unique_together constraint).  Consuming a challenge is a single atomic
    DELETE … WHERE user_id=? AND token=? AND expires_at > now(), which
    avoids the get-then-delete race of the previous cache-based approach.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_challenges",
    )
    token = models.CharField(max_length=64)
    expires_at = models.DateTimeField()

    class Meta:
        # Enforce at most one pending challenge per user.
        unique_together = [("user",)]
        verbose_name = "Security Challenge"
        verbose_name_plural = "Security Challenges"

    @classmethod
    def issue(cls, user, ttl_seconds: int = 300) -> str:
        """Create (or replace) a challenge for *user* and return the raw token."""
        from datetime import timedelta

        token = __import__("secrets").token_hex(8)
        cls.objects.update_or_create(
            user=user,
            defaults={
                "token": token,
                "expires_at": timezone.now() + timedelta(seconds=ttl_seconds),
            },
        )
        return token

    @classmethod
    def consume(cls, user, token: str) -> bool:
        """
        Atomically validate and delete the challenge in one DB round-trip.

        Returns True if the challenge existed, matched, and was not expired.
        The conditional DELETE is a single SQL statement — no race window.
        """
        deleted_count, _ = cls.objects.filter(
            user=user,
            token=token,
            expires_at__gt=timezone.now(),
        ).delete()
        return deleted_count > 0

