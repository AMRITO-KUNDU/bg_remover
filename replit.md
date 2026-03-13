# ClearCut — Background Remover

A web application that removes image backgrounds using the BiRefNet AI model (state-of-the-art as of 2024), served by a FastAPI backend.

## Architecture

- **Backend**: FastAPI (Python) — serves both the REST API and the static frontend
- **Frontend**: Single static HTML page (`static/index.html`)
- **AI Model**: BiRefNet (`birefnet-general`) via rembg + ONNX Runtime
- **Post-processing**: Alpha matting (PyMatting) for clean soft edges (hair, fur, glass)

## Background Removal Pipeline

```
Upload
  → Pillow: open, validate, convert to RGBA
  → Downscale to max 1500px longest side (for inference speed)
  → rembg / BiRefNet: generate high-quality alpha mask
  → Alpha matting: refine edges (hair, transparent areas)
  → Upscale mask back to original dimensions
  → Pillow: save as optimised PNG
  → LRU cache: SHA-256 keyed, 20 entries
  → Response
```

## Project Structure

```
app/
  main.py       — FastAPI app, lifespan (model pre-load), routes
  bg_remove.py  — Image processing: BiRefNet + alpha matting + LRU cache
static/
  index.html    — Full single-page frontend (no framework)
  favicon.ico
run.py          — Dev server entrypoint (uvicorn, 0.0.0.0:5000)
requirements.txt
```

## Key Configuration (environment variables)

| Variable            | Default              | Description                              |
|---------------------|----------------------|------------------------------------------|
| `REMBG_MODEL`       | `birefnet-general`   | rembg model name                         |
| `MAX_PROCESS_PX`    | `1500`               | Longest side for inference (px)          |
| `ALPHA_MATTING`     | `true`               | Enable alpha matting for edge refinement |
| `AM_FG_THRESHOLD`   | `240`                | Alpha matting foreground threshold       |
| `AM_BG_THRESHOLD`   | `10`                 | Alpha matting background threshold       |
| `AM_ERODE_SIZE`     | `10`                 | Alpha matting erode size                 |
| `MAX_UPLOAD_BYTES`  | `10485760` (10 MB)   | Max upload file size                     |
| `MAX_CONCURRENT_JOBS` | `2`               | Max parallel inference jobs              |
| `RESULT_CACHE_SIZE` | `20`                 | LRU cache entry count                    |

## Model Info

- **BiRefNet-general** (`birefnet-general.onnx`, ~973 MB)
  - State-of-the-art bilateral reference network for dichotomous image segmentation
  - Significantly better than U2Net for hair, fine details, and complex backgrounds
  - Downloaded automatically to `.local/share/.u2net/` on first startup

## API Endpoints

- `GET /`          — Serves `static/index.html`
- `GET /health`    — Health check → `{"status": "ok"}`
- `POST /remove-bg` — Multipart image upload → transparent PNG

## Development

```bash
python run.py   # starts uvicorn on 0.0.0.0:5000 with reload
```

## Production Deployment

Configured for **autoscale** deployment:
```
gunicorn -k uvicorn.workers.UvicornWorker app.main:app \
  --bind=0.0.0.0:5000 --workers=1 --timeout=120
```
