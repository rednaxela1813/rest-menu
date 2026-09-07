from django import forms

from .image_utils import optimize_menu_image
from .models import MenuItem


class MenuItemAdminForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = "__all__"

    def clean_image(self):
        image = self.cleaned_data.get("image")

        if not image:
            return image

        if "image" not in self.changed_data:
            return image

        return optimize_menu_image(image)
