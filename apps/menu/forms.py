from django import forms

from .image_utils import optimize_menu_image
from .models import MenuItem


class MenuItemAdminForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = [
    "restaurant",
    "category",
    "name_sk",
    "name_en",
    "slug",
    "short_description_sk",
    "short_description_en",
    "description_sk",
    "description_en",
    "price",
    "image",
    "allergens",
    "is_active",
    "is_available",
    "is_featured",
    "sort_order",
    "preparation_station",
    "estimated_preparation_minutes",
      ]

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if not image:
            return image

        if "image" not in self.changed_data:
            return image

        return optimize_menu_image(image)
