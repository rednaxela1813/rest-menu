from django.contrib import admin
from django.utils.html import format_html

from .models import Restaurant


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ["name", "currency", "default_language", "is_active"]
    list_filter = ["is_active", "currency"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["public_id", "created_at", "updated_at", "logo_preview"]
    fields = [
        "name",
        "slug",
        "description",
        "logo",
        "logo_preview",
        "currency",
        "default_language",
        "order_status_reset_minutes",
        "is_active",
        "public_id",
        "created_at",
        "updated_at",
    ]

    @admin.display(description="Náhľad loga")
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height:80px;">', obj.logo.url)
        return "—"
