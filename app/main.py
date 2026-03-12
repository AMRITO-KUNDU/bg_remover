import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

from app.bg_remove import load_model, remove_background, ImageProcessingError

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", 2))

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _semaphore
    _semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
    warmup_task = asyncio.create_task(run_in_threadpool(load_model))
    yield
    warmup_task.cancel()


app = FastAPI(title="Background Remover", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/remove-bg")
async def remove_bg(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    total = 0
    chunks = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 10 MB)")
        chunks.append(chunk)

    if not chunks:
        raise HTTPException(status_code=400, detail="Empty upload")

    image_bytes = b"".join(chunks)

    original_stem = Path(file.filename or "image").stem
    output_filename = f"{original_stem}-no-bg.png"

    try:
        async with _semaphore:
            output = await run_in_threadpool(remove_background, image_bytes)
    except ImageProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Unexpected error during background removal")
        raise HTTPException(status_code=500, detail="Background removal failed")

    return Response(
        content=output,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{output_filename}"'},
    )
