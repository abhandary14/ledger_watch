import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.organizations.models import Organization
from apps.users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        EMPLOYEE = "employee", "Employee"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="users",
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["organization"]

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "role"],
                condition=models.Q(role="owner"),
                name="unique_owner_per_org",
            )
        ]

    def __str__(self) -> str:
        return self.email
