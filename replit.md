# Background Remover

A web application that removes backgrounds from images using AI (rembg / U2Net model).

## Architecture

- **Backend**: FastAPI (Python) serving both the API and static frontend
- **Frontend**: Single static HTML page (`static/index.html`) served by FastAPI
- **AI Model**: `rembg` library backed by ONNX Runtime (U2Net model, downloaded on first use)

## Project Structure

```
app/
  main.py       - FastAPI app, routes, upload handling
  bg_remove.py  - Image processing with rembg
static/
  index.html    - Single-page frontend UI
  favicon.ico
run.py          - Development server entrypoint (uvicorn, port 5000, 0.0.0.0)
requirements.txt
```

## Key Configuration

- **Dev server**: `python run.py` — uvicorn on `0.0.0.0:5000` with reload
- **Production**: gunicorn + uvicorn workers on port 5000 (autoscale deployment)
- **Max upload size**: 10 MB (env: `MAX_UPLOAD_BYTES`)
- **Max concurrent jobs**: 2 (env: `MAX_CONCURRENT_JOBS`)
- **Max image pixels**: 40M (env: `MAX_IMAGE_PIXELS`)

## API Endpoints

- `GET /` — Serves `static/index.html`
- `GET /health` — Health check, returns `{"status": "ok"}`
- `POST /remove-bg` — Accepts multipart image upload, returns PNG with transparent background

## Notes

- The rembg model (`u2net.onnx`) is downloaded automatically on first use via `pooch`
- First background removal request may be slow due to model loading
