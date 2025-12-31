from rembg import remove
from PIL import Image
import io

def remove_background(image_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(image_bytes))
    result = remove(image)

    buffer = io.BytesIO()
    result.save(buffer, format="PNG")
    return buffer.getvalue()
