"""Role-based access mixins and decorators for staff views."""
from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.urls import reverse


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


class WaiterRequiredMixin(RoleRequiredMixin):
    required_role_attr = "is_waiter"


def role_required(role_attr: str) -> Callable:
    """Function-view decorator enforcing a role flag (e.g. ``is_cashier``)."""

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), reverse("accounts:login"))
            if not getattr(request.user, role_attr, False):
                raise PermissionDenied("Nemáte oprávnenie pre túto akciu.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
