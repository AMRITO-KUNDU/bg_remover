import io
import os
from rembg import remove
from PIL import Image, UnidentifiedImageError


class ImageProcessingError(Exception):
    pass


def remove_background(image_bytes: bytes) -> bytes:
    try:
        max_pixels = int(os.environ.get("MAX_IMAGE_PIXELS", 40_000_000))
        Image.MAX_IMAGE_PIXELS = max_pixels
        image = Image.open(io.BytesIO(image_bytes))
        if image.width * image.height > max_pixels:
            raise ImageProcessingError("Image dimensions too large")
        image = image.convert("RGBA")
    except UnidentifiedImageError:
        raise ImageProcessingError("Uploaded file is not a valid image")
    except Image.DecompressionBombError:
        raise ImageProcessingError("Uploaded image is too large to process safely")

    result = remove(image)

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.read()
