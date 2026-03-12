import hashlib
import io
import logging
import os
import threading
from collections import OrderedDict
from typing import Optional

from PIL import Image, UnidentifiedImageError
from rembg import new_session, remove

logger = logging.getLogger(__name__)

MAX_PIXELS = int(os.environ.get("MAX_IMAGE_PIXELS", 40_000_000))
CACHE_MAX_ENTRIES = int(os.environ.get("RESULT_CACHE_SIZE", 20))

_session = None
_session_lock = threading.Lock()
_cache: OrderedDict[str, bytes] = OrderedDict()


class ImageProcessingError(Exception):
    pass


def load_model() -> None:
    _get_session()


def _get_session():
    global _session
    if _session is not None:
        return _session

    with _session_lock:
        if _session is not None:
            return _session

        logger.info("Loading rembg model (u2net)...")
        _session = new_session("u2net")
        logger.info("rembg model ready.")
        return _session


def _cache_get(key: str) -> Optional[bytes]:
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    return None


def _cache_set(key: str, value: bytes) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)


def remove_background(image_bytes: bytes) -> bytes:
    cache_key = hashlib.sha256(image_bytes).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info("Cache hit for image %s", cache_key[:12])
        return cached

    try:
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        image = Image.open(io.BytesIO(image_bytes))
        if image.width * image.height > MAX_PIXELS:
            raise ImageProcessingError("Image dimensions too large")
        image = image.convert("RGBA")
    except UnidentifiedImageError:
        raise ImageProcessingError("Uploaded file is not a valid image")
    except Image.DecompressionBombError:
        raise ImageProcessingError("Uploaded image is too large to process safely")

    result = remove(image, session=_get_session())

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    output = buffer.getvalue()

    _cache_set(cache_key, output)
    return output
