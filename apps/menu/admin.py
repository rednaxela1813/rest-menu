from django.contrib import admin
from django.utils.html import format_html
from .forms import MenuItemAdminForm


from .models import (
    Allergen,
    MenuCategory,
    MenuItem,
    MenuItemModifierGroup,
    ModifierGroup,
    ModifierOption,
)


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "description"]
    search_fields = ["code", "name"]


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ["name_sk", "restaurant", "sort_order", "is_active"]
    list_filter = ["restaurant", "is_active"]
    list_editable = ["sort_order", "is_active"]
    search_fields = ["name_sk", "name_en", "slug"]
    prepopulated_fields = {"slug": ("name_sk",)}


class MenuItemModifierGroupInline(admin.TabularInline):
    model = MenuItemModifierGroup
    extra = 1
    autocomplete_fields = ["modifier_group"]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    form = MenuItemAdminForm
    list_display = [
        "name_sk",
        "category",
        "price",
        "is_active",
        "is_available",
        "is_featured",
        "image_preview",
    ]
    list_filter = ["restaurant", "category", "is_active", "is_available", "is_featured"]
    list_editable = ["is_active", "is_available", "is_featured"]
    search_fields = ["name_sk", "name_en", "slug"]
    prepopulated_fields = {"slug": ("name_sk",)}
    filter_horizontal = ["allergens"]
    inlines = [MenuItemModifierGroupInline]
    readonly_fields = ["public_id", "created_at", "updated_at", "image_preview"]
    actions = ["mark_available", "mark_unavailable"]

    @admin.display(description="Náhľad")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:50px;">', obj.image.url)
        return "—"

    @admin.action(description="Označiť ako dostupné")
    def mark_available(self, request, queryset):
        queryset.update(is_available=True)

    @admin.action(description="Označiť ako nedostupné")
    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)


class ModifierOptionInline(admin.TabularInline):
    model = ModifierOption
    extra = 2


@admin.register(ModifierGroup)
class ModifierGroupAdmin(admin.ModelAdmin):
    list_display = [
        "name_sk",
        "parent",
        "selection_type",
        "min_selections",
        "max_selections",
        "is_required",
        "collapsed_by_default",
        "menu_item_source_category",
    ]
    list_filter = [
        "selection_type",
        "is_required",
        "collapsed_by_default",
        "is_active",
        "parent",
        "menu_item_source_category",
    ]
    list_editable = ["collapsed_by_default"]
    search_fields = ["name_sk", "name_en"]
    # `parent` turns a group into a subcategory (e.g. Pivo under Nápoj). A group
    # with a parent is a leaf with options; a group with children is a container.
    autocomplete_fields = ["parent", "menu_item_source_category"]
    inlines = [ModifierOptionInline]


@admin.register(ModifierOption)
class ModifierOptionAdmin(admin.ModelAdmin):
    list_display = ["name_sk", "group", "price_delta", "is_default", "is_active"]
    list_filter = ["group", "is_active", "is_default"]
    search_fields = ["name_sk", "name_en"]
