import asyncio
import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from app.bg_remove import remove_background, ImageProcessingError
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Simple Background Remover")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", 2))
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


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
            raise HTTPException(status_code=413, detail="File too large")
        chunks.append(chunk)

    if not chunks:
        raise HTTPException(status_code=400, detail="Empty upload")

    image_bytes = b"".join(chunks)

    try:
        async with _semaphore:
            output = await run_in_threadpool(remove_background, image_bytes)
    except ImageProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Background removal failed")

    return Response(content=output, media_type="image/png")
