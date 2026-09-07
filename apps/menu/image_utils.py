from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image, ImageOps


def optimize_menu_image(
    uploaded_file,
    *,
    max_size: tuple[int, int] = (1600, 1600),
    quality: int = 82,
):
    uploaded_file.seek(0)

    with Image.open(uploaded_file) as image:
        if image.format not in {"JPEG", "PNG"}:
            uploaded_file.seek(0)
            return uploaded_file

        image = ImageOps.exif_transpose(image)

        has_alpha = (
            image.mode in ("RGBA", "LA")
            or (image.mode == "P" and "transparency" in image.info)
        )

        image = image.convert("RGBA" if has_alpha else "RGB")

        image.thumbnail(
            max_size,
            Image.Resampling.LANCZOS,
        )

        output = BytesIO()

        image.save(
            output,
            format="WEBP",
            quality=quality,
            method=6,
        )

    filename = f"{Path(uploaded_file.name).stem}-{uuid4().hex[:8]}.webp"

    return SimpleUploadedFile(
        name=filename,
        content=output.getvalue(),
        content_type="image/webp",
    )
