"""Order aggregate: orders, items, item modifiers and status history."""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import PublicIDModel, TimeStampedModel

from .states import GUEST_STATUS_TEXT, OrderSource, OrderStatus


class Order(PublicIDModel, TimeStampedModel):
    order_number = models.CharField(_("číslo objednávky"), max_length=20, unique=True, db_index=True)
    restaurant = models.ForeignKey(
        "restaurants.Restaurant", on_delete=models.PROTECT, related_name="orders"
    )
    table = models.ForeignKey(
        "tables.DiningTable",
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    status = models.CharField(
        _("stav"), max_length=20, choices=OrderStatus.choices, default=OrderStatus.NEW, db_index=True
    )
    source = models.CharField(_("zdroj"), max_length=10, choices=OrderSource.choices)
    customer_comment = models.TextField(_("poznámka hosťa"), blank=True)

    subtotal = models.DecimalField(_("medzisúčet"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(_("spolu"), max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(_("mena"), max_length=3, default="EUR")

    # Idempotency key prevents duplicate orders from a double submit.
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    # Optimistic locking guard against concurrent edits.
    version = models.PositiveIntegerField(default=1)

    confirmed_at = models.DateTimeField(null=True, blank=True)
    preparation_started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_orders"
    )
    confirmed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="confirmed_orders"
    )
    cancelled_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="cancelled_orders"
    )

    class Meta:
        verbose_name = _("objednávka")
        verbose_name_plural = _("objednávky")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self) -> str:
        return f"#{self.order_number}"

    @property
    def guest_status_text(self) -> str:
        return GUEST_STATUS_TEXT.get(self.status, self.get_status_display())

    @property
    def short_number(self) -> str:
        from .numbering import short_display_number

        return short_display_number(self.order_number)

    @property
    def is_closed(self) -> bool:
        from .states import CLOSED_STATUSES

        return self.status in CLOSED_STATUSES

    @property
    def total_quantity(self) -> int:
        return sum(item.quantity for item in self.items.all())

    def recalculate_totals(self, *, commit: bool = True) -> None:
        subtotal = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
        self.subtotal = subtotal
        self.total = subtotal
        if commit:
            self.save(update_fields=["subtotal", "total", "updated_at"])


class OrderItem(PublicIDModel, TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "menu.MenuItem", on_delete=models.PROTECT, related_name="order_items"
    )
    # Snapshots: history must not change when the menu price/name changes later.
    item_name_snapshot = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    customer_comment = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.NEW
    )

    class Meta:
        verbose_name = _("položka objednávky")
        verbose_name_plural = _("položky objednávky")
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.item_name_snapshot}"

    @property
    def modifiers_delta(self) -> Decimal:
        return sum((m.total_delta for m in self.modifiers.all()), Decimal("0.00"))

    def recalculate(self, *, commit: bool = True) -> None:
        """unit_price = base + sum(modifier deltas); line_total = unit_price * qty."""
        base = self.menu_item.price if self.menu_item_id else self.unit_price
        per_unit_mods = sum((m.price_delta * m.quantity for m in self.modifiers.all()), Decimal("0.00"))
        self.unit_price = (base + per_unit_mods).quantize(Decimal("0.01"))
        self.line_total = (self.unit_price * self.quantity).quantize(Decimal("0.01"))
        if commit:
            self.save(update_fields=["unit_price", "line_total", "updated_at"])


class OrderItemModifier(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name="modifiers")
    modifier_option = models.ForeignKey(
        "menu.ModifierOption",
        on_delete=models.PROTECT,
        related_name="order_item_modifiers",
        null=True,
        blank=True,
    )
    modifier_menu_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.PROTECT,
        related_name="order_item_menu_modifiers",
        null=True,
        blank=True,
    )
    group_name_snapshot = models.CharField(max_length=150)
    option_name_snapshot = models.CharField(max_length=150)
    price_delta = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    quantity = models.PositiveIntegerField(default=1)
    total_delta = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("modifikátor položky")
        verbose_name_plural = _("modifikátory položiek")

    def __str__(self) -> str:
        return self.option_name_snapshot

    def save(self, *args, **kwargs) -> None:
        self.total_delta = (self.price_delta * self.quantity).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    previous_status = models.CharField(max_length=20, choices=OrderStatus.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=OrderStatus.choices)
    changed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True
    )
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("história stavu")
        verbose_name_plural = _("história stavov")
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.order}: {self.previous_status} → {self.new_status}"
