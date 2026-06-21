from django.contrib import admin

from .models import Order, OrderItem, OrderItemModifier, OrderStatusHistory


class OrderItemModifierInline(admin.TabularInline):
    model = OrderItemModifier
    extra = 0
    readonly_fields = ["group_name_snapshot", "option_name_snapshot", "price_delta", "total_delta"]
    can_delete = False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["item_name_snapshot", "unit_price", "quantity", "line_total"]
    can_delete = False
    show_change_link = True


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["previous_status", "new_status", "changed_by", "comment", "created_at"]
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "table", "status", "source", "total", "created_at"]
    list_filter = ["status", "source", "restaurant", "created_at"]
    search_fields = ["order_number", "public_id"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    readonly_fields = [
        "public_id",
        "order_number",
        "subtotal",
        "total",
        "version",
        "idempotency_key",
        "created_at",
        "confirmed_at",
        "preparation_started_at",
        "ready_at",
        "served_at",
        "cancelled_at",
    ]

    # Orders are never physically deleted via the UI; cancel via status instead.
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "item_name_snapshot", "quantity", "unit_price", "line_total"]
    search_fields = ["order__order_number", "item_name_snapshot"]
    inlines = [OrderItemModifierInline]
    readonly_fields = ["item_name_snapshot", "unit_price", "line_total"]

    def has_delete_permission(self, request, obj=None):
        return False
