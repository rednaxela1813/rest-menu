"""Staff authentication views."""
from __future__ import annotations

from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import View


class StaffLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class StaffLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


class PostLoginRedirectView(View):
    """Send each role to its default workspace after login."""

    def get(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect("accounts:login")
        if user.is_kitchen and not user.is_cashier:
            return redirect("kitchen:board")
        if user.is_cashier:
            return redirect("cashier:board")
        return redirect("admin:index")
