"""Menu domain: categories, items, allergens and modifiers."""
from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from apps.common.models import PublicIDModel, TimeStampedModel


def _localized(obj, base: str) -> str:
    """Return the field value for the active language, falling back to sk."""
    lang = (get_language() or "sk")[:2]
    value = getattr(obj, f"{base}_{lang}", "") if lang in {"sk", "en"} else ""
    return value or getattr(obj, f"{base}_sk", "") or getattr(obj, f"{base}_en", "")


class Allergen(models.Model):
    code = models.CharField(_("kód"), max_length=10, unique=True)
    name = models.CharField(_("názov"), max_length=120)
    description = models.CharField(_("popis"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("alergén")
        verbose_name_plural = _("alergény")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"


class MenuCategory(PublicIDModel, TimeStampedModel):
    restaurant = models.ForeignKey(
        "restaurants.Restaurant", on_delete=models.CASCADE, related_name="categories"
    )
    name_sk = models.CharField(_("názov (SK)"), max_length=150)
    name_en = models.CharField(_("názov (EN)"), max_length=150, blank=True)
    slug = models.SlugField(_("slug"), max_length=150)
    description_sk = models.TextField(_("popis (SK)"), blank=True)
    description_en = models.TextField(_("popis (EN)"), blank=True)
    image = models.ImageField(upload_to="menu/categories/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(_("poradie"), default=0)
    is_active = models.BooleanField(_("aktívna"), default=True)
    available_from = models.TimeField(_("dostupné od"), blank=True, null=True)
    available_until = models.TimeField(_("dostupné do"), blank=True, null=True)

    class Meta:
        verbose_name = _("kategória")
        verbose_name_plural = _("kategórie")
        ordering = ["sort_order", "name_sk"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "slug"], name="unique_category_slug_per_restaurant"
            )
        ]

    def __str__(self) -> str:
        return self.name_sk

    @property
    def name(self) -> str:
        return _localized(self, "name")

    @property
    def description(self) -> str:
        return _localized(self, "description")

    def is_available_now(self) -> bool:
        if not self.is_active:
            return False
        if self.available_from and self.available_until:
            now = timezone.localtime().time()
            return self.available_from <= now <= self.available_until
        return True


class MenuItem(PublicIDModel, TimeStampedModel):
    restaurant = models.ForeignKey(
        "restaurants.Restaurant", on_delete=models.CASCADE, related_name="items"
    )
    category = models.ForeignKey(
        MenuCategory, on_delete=models.PROTECT, related_name="items", verbose_name=_("kategória")
    )
    name_sk = models.CharField(_("názov (SK)"), max_length=200)
    name_en = models.CharField(_("názov (EN)"), max_length=200, blank=True)
    slug = models.SlugField(_("slug"), max_length=200)
    short_description_sk = models.CharField(_("krátky popis (SK)"), max_length=255, blank=True)
    short_description_en = models.CharField(_("krátky popis (EN)"), max_length=255, blank=True)
    description_sk = models.TextField(_("popis (SK)"), blank=True)
    description_en = models.TextField(_("popis (EN)"), blank=True)
    price = models.DecimalField(
        _("cena"), max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    image = models.ImageField(upload_to="menu/items/", blank=True, null=True)
    allergens = models.ManyToManyField(Allergen, blank=True, related_name="items")
    # is_active=False hides the item permanently; is_available=False is a
    # temporary "sold out" toggle that keeps the item visible but unorderable.
    is_active = models.BooleanField(_("aktívna položka"), default=True)
    is_available = models.BooleanField(_("momentálne dostupná"), default=True)
    is_featured = models.BooleanField(_("odporúčané"), default=False)
    sort_order = models.PositiveIntegerField(_("poradie"), default=0)
    preparation_station = models.CharField(_("stanica prípravy"), max_length=50, blank=True)
    estimated_preparation_minutes = models.PositiveIntegerField(_("odhad prípravy (min)"), default=10)

    modifier_groups = models.ManyToManyField(
        "menu.ModifierGroup", through="menu.MenuItemModifierGroup", related_name="items"
    )

    class Meta:
        verbose_name = _("položka menu")
        verbose_name_plural = _("položky menu")
        ordering = ["sort_order", "name_sk"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "slug"], name="unique_item_slug_per_restaurant"
            )
        ]

    def __str__(self) -> str:
        return self.name_sk

    @property
    def name(self) -> str:
        return _localized(self, "name")

    @property
    def short_description(self) -> str:
        return _localized(self, "short_description")

    @property
    def description(self) -> str:
        return _localized(self, "description")

    @property
    def can_be_ordered(self) -> bool:
        return self.is_active and self.is_available


class ModifierGroup(PublicIDModel, TimeStampedModel):
    class SelectionType(models.TextChoices):
        SINGLE = "SINGLE", _("Jeden výber")
        MULTIPLE = "MULTIPLE", _("Viacnásobný výber")

    name_sk = models.CharField(_("názov (SK)"), max_length=150)
    name_en = models.CharField(_("názov (EN)"), max_length=150, blank=True)
    selection_type = models.CharField(
        _("typ výberu"), max_length=10, choices=SelectionType.choices, default=SelectionType.SINGLE
    )
    min_selections = models.PositiveIntegerField(_("min. výberov"), default=0)
    max_selections = models.PositiveIntegerField(_("max. výberov"), default=1)
    is_required = models.BooleanField(_("povinné"), default=False)
    # Customization groups (add/remove ingredients) are hidden behind a toggle so
    # the kitchen isn't flooded with changes; upsell groups (fries, drinks) stay
    # visible. Required groups are always shown regardless of this flag.
    collapsed_by_default = models.BooleanField(
        _("predvolene skryté (úprava zloženia)"), default=False
    )
    sort_order = models.PositiveIntegerField(_("poradie"), default=0)
    is_active = models.BooleanField(_("aktívna"), default=True)
    # A group is either a *container* (has child groups, no own options — e.g.
    # "Nápoj" → Pivo/Víno/Nealko) or a *leaf* (has options, no children). Only
    # one level of nesting is supported. For containers, min/max_selections act
    # as an optional aggregate cap across all children (0 = no aggregate limit);
    # each child keeps its own selection rules.
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name=_("nadradená skupina"),
    )
    menu_item_source_category = models.ForeignKey(
        "menu.MenuCategory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modifier_groups",
        verbose_name=_("položky z kategórie menu"),
        help_text=_("Ak je vyplnené, skupina ponúkne aktívne položky z tejto kategórie ako doplnky."),
    )

    class Meta:
        verbose_name = _("skupina modifikátorov")
        verbose_name_plural = _("skupiny modifikátorov")
        ordering = ["sort_order", "name_sk"]

    def __str__(self) -> str:
        return self.name_sk

    @property
    def name(self) -> str:
        return _localized(self, "name")

    @property
    def is_container(self) -> bool:
        """True if this group groups child subcategories instead of options.

        Relies on the prefetched ``children`` cache when available so templates
        don't trigger a query per group.
        """
        return any(self.children.all())

    def clean(self) -> None:
        super().clean()
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError({"parent": _("Skupina nemôže byť nadradená sama sebe.")})
        # Only one level of nesting: a subgroup cannot itself have a parent.
        if self.parent and self.parent.parent_id:
            raise ValidationError(
                {"parent": _("Podporuje sa len jedna úroveň vnorenia podkategórií.")}
            )


class ModifierOption(PublicIDModel, TimeStampedModel):
    group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE, related_name="options")
    name_sk = models.CharField(_("názov (SK)"), max_length=150)
    name_en = models.CharField(_("názov (EN)"), max_length=150, blank=True)
    price_delta = models.DecimalField(
        _("doplatok"), max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    is_default = models.BooleanField(_("predvolené"), default=False)
    is_active = models.BooleanField(_("aktívne"), default=True)
    sort_order = models.PositiveIntegerField(_("poradie"), default=0)

    class Meta:
        verbose_name = _("modifikátor")
        verbose_name_plural = _("modifikátory")
        ordering = ["sort_order", "name_sk"]

    def __str__(self) -> str:
        return self.name_sk

    @property
    def name(self) -> str:
        return _localized(self, "name")


class MenuItemModifierGroup(models.Model):
    """Through model so each item can override the group's selection rules."""

    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE, related_name="item_modifier_groups"
    )
    modifier_group = models.ForeignKey(
        ModifierGroup, on_delete=models.CASCADE, related_name="item_links"
    )
    sort_order = models.PositiveIntegerField(_("poradie"), default=0)
    is_required = models.BooleanField(_("povinné pre túto položku"), default=False)
    min_selections_override = models.PositiveIntegerField(_("min. (override)"), null=True, blank=True)
    max_selections_override = models.PositiveIntegerField(_("max. (override)"), null=True, blank=True)

    class Meta:
        verbose_name = _("priradenie modifikátorov")
        verbose_name_plural = _("priradenia modifikátorov")
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["menu_item", "modifier_group"], name="unique_item_modifier_group"
            )
        ]

    def __str__(self) -> str:
        return f"{self.menu_item} · {self.modifier_group}"

    @property
    def effective_min(self) -> int:
        if self.min_selections_override is not None:
            return self.min_selections_override
        return self.modifier_group.min_selections

    @property
    def effective_max(self) -> int:
        if self.max_selections_override is not None:
            return self.max_selections_override
        return self.modifier_group.max_selections

    @property
    def effective_required(self) -> bool:
        return self.is_required or self.modifier_group.is_required
