from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "action", "user", "object_type", "object_id", "ip_address"]
    list_filter = ["action", "object_type", "created_at"]
    search_fields = ["description", "object_id", "user__email"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "user",
        "action",
        "object_type",
        "object_id",
        "description",
        "metadata",
        "ip_address",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
