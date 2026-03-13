"""
Background removal using rembg with BiRefNet (state-of-the-art model).

Pipeline:
  1. Open & validate image with Pillow
  2. Downscale if the image exceeds MAX_PROCESS_PX on its longest side
     (BiRefNet produces excellent results at 1500 px; going larger gives
     diminishing returns but slows inference significantly)
  3. Run rembg / BiRefNet to produce an RGBA mask
  4. Apply alpha matting to refine soft edges (hair, fur, transparent glass)
  5. Upscale the mask back to the original dimensions if we downscaled
  6. Cache the result by SHA-256 of the raw input bytes (LRU, configurable)
"""

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

# ── Tunables (all overridable via environment variables) ──────────────────────
MODEL_NAME       = os.environ.get("REMBG_MODEL",        "birefnet-general")
MAX_PIXELS       = int(os.environ.get("MAX_IMAGE_PIXELS", 40_000_000))
MAX_PROCESS_PX   = int(os.environ.get("MAX_PROCESS_PX",  1_500))   # longest side
ALPHA_MATTING    = os.environ.get("ALPHA_MATTING", "true").lower() == "true"
AM_FG_THRESHOLD  = int(os.environ.get("AM_FG_THRESHOLD", 240))
AM_BG_THRESHOLD  = int(os.environ.get("AM_BG_THRESHOLD", 10))
AM_ERODE_SIZE    = int(os.environ.get("AM_ERODE_SIZE",   10))
CACHE_MAX        = int(os.environ.get("RESULT_CACHE_SIZE", 20))

# ── Internal state ────────────────────────────────────────────────────────────
_session      = None
_session_lock = threading.Lock()
_cache: OrderedDict[str, bytes] = OrderedDict()


class ImageProcessingError(Exception):
    pass


# ── Session (loaded once at startup) ─────────────────────────────────────────
def load_model() -> None:
    """Pre-warm the model at server startup so the first request is fast."""
    _get_session()


def _get_session():
    global _session
    if _session is not None:
        return _session
    with _session_lock:
        if _session is not None:
            return _session
        logger.info("Loading rembg model: %s", MODEL_NAME)
        _session = new_session(MODEL_NAME)
        logger.info("Model ready: %s", MODEL_NAME)
        return _session


# ── LRU result cache ──────────────────────────────────────────────────────────
def _cache_get(key: str) -> Optional[bytes]:
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    return None


def _cache_set(key: str, value: bytes) -> None:
    _cache[key] = value
    _cache.move_to_end(key)
    while len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)


# ── Image helpers ─────────────────────────────────────────────────────────────
def _downscale(image: Image.Image) -> tuple[Image.Image, float]:
    """
    Shrink to MAX_PROCESS_PX on the longest side.
    Returns (scaled_image, scale_factor).  scale_factor == 1.0 means no change.
    """
    w, h = image.size
    longest = max(w, h)
    if longest <= MAX_PROCESS_PX:
        return image, 1.0
    scale = MAX_PROCESS_PX / longest
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    logger.debug("Downscaling %dx%d → %dx%d for inference", w, h, new_w, new_h)
    return image.resize((new_w, new_h), Image.LANCZOS), scale


def _upscale_alpha(result: Image.Image, original_size: tuple[int, int]) -> Image.Image:
    """Resize the RGBA result back to the original image dimensions."""
    if result.size == original_size:
        return result
    return result.resize(original_size, Image.LANCZOS)


# ── Public API ────────────────────────────────────────────────────────────────
def remove_background(image_bytes: bytes) -> bytes:
    # 1. Cache lookup
    cache_key = hashlib.sha256(image_bytes).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info("Cache hit %s", cache_key[:12])
        return cached

    # 2. Open & validate
    try:
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        original = Image.open(io.BytesIO(image_bytes))
        if original.width * original.height > MAX_PIXELS:
            raise ImageProcessingError("Image dimensions too large")
        original = original.convert("RGBA")
    except UnidentifiedImageError:
        raise ImageProcessingError("Uploaded file is not a valid image")
    except Image.DecompressionBombError:
        raise ImageProcessingError("Uploaded image is too large to process safely")

    original_size = original.size

    # 3. Downscale for inference
    inference_img, scale = _downscale(original)

    # 4. Remove background (BiRefNet + optional alpha matting)
    result = remove(
        inference_img,
        session=_get_session(),
        alpha_matting=ALPHA_MATTING,
        alpha_matting_foreground_threshold=AM_FG_THRESHOLD,
        alpha_matting_background_threshold=AM_BG_THRESHOLD,
        alpha_matting_erode_size=AM_ERODE_SIZE,
    )

    # 5. Restore original dimensions if we downscaled
    result = _upscale_alpha(result, original_size)

    # 6. Encode to PNG and cache
    buffer = io.BytesIO()
    result.save(buffer, format="PNG", optimize=True)
    output = buffer.getvalue()

    _cache_set(cache_key, output)
    logger.info("Processed %dx%d image (scale=%.2f, matting=%s)",
                original_size[0], original_size[1], scale, ALPHA_MATTING)
    return output
