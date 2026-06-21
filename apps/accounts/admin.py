from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "role", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["public_id", "created_at", "updated_at", "last_login"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Osobné údaje"), {"fields": ("first_name", "last_name")}),
        (_("Rola a prístup"), {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        (_("Oprávnenia"), {"fields": ("groups", "user_permissions"), "classes": ("collapse",)}),
        (_("Metadáta"), {"fields": ("public_id", "last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
            },
        ),
    )
