"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.restaurants.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health"),
    path("accounts/", include("apps.accounts.urls")),
    path("staff/cashier/", include("apps.cashier.urls")),
    path("staff/kitchen/", include("apps.kitchen.urls")),
    path("", include("apps.menu.urls")),
    path("", include("apps.tables.urls")),
    path("", include("apps.orders.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
