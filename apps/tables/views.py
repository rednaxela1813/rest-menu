"""Guest table entry point and QR downloads."""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect

from apps.accounts.permissions import role_required

from .models import DiningTable
from .services import render_qr_png, render_tables_pdf


def _base_url(request) -> str:
    """Prefer the configured public base URL; fall back to the request host.

    Using the request host embeds 'localhost' into the QR when the admin opens
    the site locally — phones then can't reach it. PUBLIC_BASE_URL fixes that.
    """
    return settings.PUBLIC_BASE_URL or request.build_absolute_uri("/")


def table_menu(request, number: int, token):
    """Validate the table+token, bind the guest session to the table, show menu."""
    table = get_object_or_404(DiningTable, number=number, qr_token=token)
    if not table.is_active:
        return HttpResponse(
            "Tento stôl momentálne neprijíma objednávky. Kontaktujte prosím obsluhu.",
            status=410,
        )
    # Bind the guest session to this table; the table id is never trusted from
    # form fields, only from this server-side session value.
    request.session["table_id"] = table.id
    request.session["table_token"] = str(table.qr_token)
    return redirect("menu:guest_menu")


@role_required("is_admin_role")
def table_qr_png(request, pk: int):
    table = get_object_or_404(DiningTable, pk=pk)
    url = table.build_menu_url(_base_url(request))
    png = render_qr_png(url)
    response = HttpResponse(png, content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="table-{table.number}-qr.png"'
    return response


@role_required("is_admin_role")
def tables_qr_pdf(request):
    base = _base_url(request)
    tables = DiningTable.objects.filter(is_active=True).order_by("sort_order", "number")
    data = [(str(t), t.build_menu_url(base)) for t in tables]
    pdf = render_tables_pdf(data)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="tables-qr.pdf"'
    return response
