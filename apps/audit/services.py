"""Helper to write audit entries from anywhere in the codebase."""
from __future__ import annotations

from .models import AuditLog


def record_action(
    *,
    user=None,
    action: str,
    obj=None,
    description: str = "",
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    object_type = obj.__class__.__name__ if obj is not None else ""
    object_id = str(getattr(obj, "public_id", getattr(obj, "pk", ""))) if obj is not None else ""
    return AuditLog.objects.create(
        user=user if (user and getattr(user, "pk", None)) else None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        description=description,
        metadata=metadata or {},
        ip_address=ip_address,
    )
