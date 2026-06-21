"""Health-check endpoint covering DB and cache/redis."""
from __future__ import annotations

from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def health_check(request):
    checks = {"django": "ok"}
    status = 200

    try:
        connections["default"].cursor()
        checks["database"] = "ok"
    except OperationalError:
        checks["database"] = "error"
        status = 503

    try:
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        checks["channel_layer"] = "ok" if layer is not None else "missing"
    except Exception:  # pragma: no cover - defensive
        checks["channel_layer"] = "error"

    checks["status"] = "ok" if status == 200 else "degraded"
    return JsonResponse(checks, status=status)
