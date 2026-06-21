"""Dining tables with unpredictable QR tokens."""
from __future__ import annotations

import uuid

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.common.models import PublicIDModel, TimeStampedModel


class DiningTable(PublicIDModel, TimeStampedModel):
    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.CASCADE,
        related_name="tables",
        verbose_name=_("prevádzka"),
    )
    number = models.PositiveIntegerField(_("číslo stola"))
    name = models.CharField(_("názov"), max_length=100, blank=True)
    # Random, hard-to-guess token used in the public URL.
    qr_token = models.UUIDField(_("QR token"), default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(_("aktívny"), default=True)
    sort_order = models.PositiveIntegerField(_("poradie"), default=0)

    class Meta:
        verbose_name = _("stôl")
        verbose_name_plural = _("stoly")
        ordering = ["sort_order", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "number"], name="unique_table_number_per_restaurant"
            )
        ]

    def __str__(self) -> str:
        return self.name or f"Stôl {self.number}"

    def regenerate_token(self) -> None:
        self.qr_token = uuid.uuid4()
        self.save(update_fields=["qr_token", "updated_at"])

    def get_menu_path(self) -> str:
        """Relative URL guests open from the QR code."""
        return reverse("tables:table_menu", kwargs={"number": self.number, "token": self.qr_token})

    def build_menu_url(self, base_url: str) -> str:
        return f"{base_url.rstrip('/')}{self.get_menu_path()}"
