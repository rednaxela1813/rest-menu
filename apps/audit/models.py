"""Append-only audit log of key staff actions."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField(_("akcia"), max_length=100, db_index=True)
    object_type = models.CharField(_("typ objektu"), max_length=100, blank=True)
    object_id = models.CharField(_("ID objektu"), max_length=64, blank=True)
    description = models.TextField(_("popis"), blank=True)
    metadata = models.JSONField(_("metadáta"), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(_("IP adresa"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("záznam denníka")
        verbose_name_plural = _("denník akcií")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} ({self.user})"
