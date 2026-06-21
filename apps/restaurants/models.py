"""Restaurant (single venue in v1, but modelled for future multi-venue)."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import PublicIDModel, TimeStampedModel


class Restaurant(PublicIDModel, TimeStampedModel):
    name = models.CharField(_("názov"), max_length=200)
    slug = models.SlugField(_("slug"), max_length=200, unique=True)
    description = models.TextField(_("popis"), blank=True)
    logo = models.ImageField(_("logo"), upload_to="restaurants/logos/", blank=True, null=True)
    currency = models.CharField(_("mena"), max_length=3, default="EUR")
    default_language = models.CharField(_("predvolený jazyk"), max_length=5, default="sk")
    is_active = models.BooleanField(_("aktívna"), default=True)
    # How long the guest's order-status chip stays visible after the order is
    # closed (served / cancelled / rejected) before it disappears and resets.
    order_status_reset_minutes = models.PositiveIntegerField(
        _("skrytie stavu objednávky (min)"), default=3
    )

    class Meta:
        verbose_name = _("prevádzka")
        verbose_name_plural = _("prevádzky")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def get_default(cls) -> Restaurant | None:
        """Single-venue helper: the first active restaurant."""
        return cls.objects.filter(is_active=True).order_by("id").first()
