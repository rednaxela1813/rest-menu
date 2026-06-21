"""Custom email-based user with restaurant roles."""
from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import PublicIDModel, TimeStampedModel

from .managers import UserManager


class UserRole(models.TextChoices):
    ADMIN = "admin", _("Administrátor")
    CASHIER = "cashier", _("Pokladník")
    KITCHEN = "kitchen", _("Kuchyňa")
    WAITER = "waiter", _("Čašník")


class User(AbstractBaseUser, PermissionsMixin, PublicIDModel, TimeStampedModel):
    email = models.EmailField(_("e-mail"), unique=True)
    first_name = models.CharField(_("meno"), max_length=150, blank=True)
    last_name = models.CharField(_("priezvisko"), max_length=150, blank=True)
    role = models.CharField(
        _("rola"), max_length=20, choices=UserRole.choices, default=UserRole.CASHIER
    )
    is_active = models.BooleanField(_("aktívny"), default=True)
    is_staff = models.BooleanField(_("prístup do administrácie"), default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        verbose_name = _("používateľ")
        verbose_name_plural = _("používatelia")
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email

    # Role helpers -------------------------------------------------------
    @property
    def is_admin_role(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_cashier(self) -> bool:
        return self.role == UserRole.CASHIER or self.is_admin_role

    @property
    def is_kitchen(self) -> bool:
        return self.role == UserRole.KITCHEN or self.is_admin_role

    @property
    def is_waiter(self) -> bool:
        return self.role == UserRole.WAITER or self.is_admin_role
