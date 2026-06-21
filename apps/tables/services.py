"""QR code rendering helpers for tables."""
from __future__ import annotations

import io

import qrcode
from qrcode.image.pil import PilImage


def render_qr_png(url: str, box_size: int = 10, border: int = 4) -> bytes:
    """Return PNG bytes for the given URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img: PilImage = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def render_tables_pdf(table_urls: list[tuple[str, str]]) -> bytes:
    """Build a printable PDF, one QR per page.

    ``table_urls`` is a list of ``(table_label, url)`` tuples.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    for label, url in table_urls:
        png = render_qr_png(url, box_size=12)
        image = ImageReader(io.BytesIO(png))
        qr_size = 12 * cm
        x = (width - qr_size) / 2
        y = (height - qr_size) / 2

        pdf.setFont("Helvetica-Bold", 28)
        pdf.drawCentredString(width / 2, y + qr_size + 2 * cm, "Naskenujte QR kód a objednajte si")
        pdf.drawImage(image, x, y, qr_size, qr_size)
        pdf.setFont("Helvetica-Bold", 36)
        pdf.drawCentredString(width / 2, y - 2 * cm, label)
        pdf.showPage()

    pdf.save()
    return buffer.getvalue()
