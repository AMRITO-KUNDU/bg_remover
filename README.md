---
title: Simple Background Remover
emoji: 🖼️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Simple Background Remover

A small web app to remove image backgrounds using FastAPI and rembg.

## Features
- Upload an image via the web interface
- Remove the background
- Download or view the result as PNG

## Requirements
- Python 3.10+
- pip

## Configuration
- `MAX_UPLOAD_BYTES` (default: 10485760) maximum upload size in bytes
- `MAX_IMAGE_PIXELS` (default: 40000000) maximum total pixels allowed
- `MAX_CONCURRENT_JOBS` (default: 2) concurrent background removal jobs
- `HOST` (default: 127.0.0.1) bind address
- `PORT` (default: 7860) bind port
- `LOG_LEVEL` (default: INFO) logging level


### Docker
Build and run:
```bash
docker build -t bg-remover .
docker run -p 7860:7860 bg-remover
```

## Installation
1. Clone the repo:
   ```bash
   git clone <repo_url>
   cd bg_remover
   ```

2. Create a virtualenv and install deps:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

3. Run locally:
   ```bash
   python run.py
   ```

   Dev reload:
   ```bash
   # PowerShell
   $env:RELOAD=1
   python run.py

   # CMD
   set RELOAD=1
   python run.py
   ```
