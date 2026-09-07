from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.menu.image_utils import optimize_menu_image


def make_image_file(
    *,
    filename: str,
    image_format: str,
    size: tuple[int, int] = (800, 600),
    mode: str = "RGB",
    color=None,
):
    if color is None:
        color = (255, 0, 0, 128) if mode == "RGBA" else (255, 0, 0)

    buffer = BytesIO()

    image = Image.new(
        mode,
        size,
        color=color,
    )

    image.save(
        buffer,
        format=image_format,
    )

    return SimpleUploadedFile(
        name=filename,
        content=buffer.getvalue(),
        content_type=f"image/{image_format.lower()}",
    )


def test_jpeg_is_converted_to_webp():
    uploaded_file = make_image_file(
        filename="burger.jpg",
        image_format="JPEG",
    )

    result = optimize_menu_image(uploaded_file)

    assert result.name.endswith(".webp")
    assert result.content_type == "image/webp"

    with Image.open(result) as image:
        assert image.format == "WEBP"
        assert image.size == (800, 600)


def test_large_image_is_resized_to_max_1600():
    uploaded_file = make_image_file(
        filename="large-burger.jpg",
        image_format="JPEG",
        size=(4000, 3000),
    )

    result = optimize_menu_image(uploaded_file)

    with Image.open(result) as image:
        assert image.format == "WEBP"
        assert image.size == (1600, 1200)
        assert image.width <= 1600
        assert image.height <= 1600


def test_transparent_png_preserves_alpha_channel():
    uploaded_file = make_image_file(
        filename="logo.png",
        image_format="PNG",
        size=(800, 600),
        mode="RGBA",
        color=(255, 0, 0, 128),
    )

    result = optimize_menu_image(uploaded_file)

    with Image.open(result) as image:
        assert image.format == "WEBP"
        assert image.mode == "RGBA"

        _, _, _, alpha = image.getpixel((0, 0))

        assert alpha < 255