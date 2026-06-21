"""Role-based access mixins and decorators for staff views."""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse


class RoleRequiredMixin(LoginRequiredMixin):
    """Restrict a class-based view to users whose role flag is set."""

    required_role_attr: str = "is_admin_role"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not getattr(request.user, self.required_role_attr, False):
            raise PermissionDenied("Nemáte oprávnenie pre túto stránku.")
        return super().dispatch(request, *args, **kwargs)


class CashierRequiredMixin(RoleRequiredMixin):
    required_role_attr = "is_cashier"


class KitchenRequiredMixin(RoleRequiredMixin):
    required_role_attr = "is_kitchen"


def role_required(role_attr: str) -> Callable:
    """Function-view decorator enforcing a role flag (e.g. ``is_cashier``)."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                raise PermissionDenied("Vyžaduje sa prihlásenie.")
            if not getattr(request.user, role_attr, False):
                raise PermissionDenied("Nemáte oprávnenie pre túto akciu.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
