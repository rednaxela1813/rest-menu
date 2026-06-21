from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import DiningTable


@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = ["__str__", "restaurant", "number", "is_active", "sort_order", "qr_links"]
    list_filter = ["restaurant", "is_active"]
    search_fields = ["number", "name"]
    list_editable = ["is_active", "sort_order"]
    readonly_fields = ["public_id", "qr_token", "created_at", "updated_at"]
    actions = ["regenerate_tokens", "activate_tables", "deactivate_tables"]

    @admin.display(description="QR kód")
    def qr_links(self, obj):
        png_url = reverse("tables:qr_png", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">Stiahnuť PNG</a>', png_url)

    @admin.action(description="Vygenerovať nové QR tokeny")
    def regenerate_tokens(self, request, queryset):
        for table in queryset:
            table.regenerate_token()
        self.message_user(request, f"Obnovených {queryset.count()} tokenov.")

    @admin.action(description="Aktivovať stoly")
    def activate_tables(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Deaktivovať stoly")
    def deactivate_tables(self, request, queryset):
        queryset.update(is_active=False)
