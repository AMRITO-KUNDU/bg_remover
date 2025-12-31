from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response, FileResponse
from app.bg_remove import remove_background
import os

app = FastAPI(title="Simple Background Remover")

@app.get("/")
def home():
    return FileResponse(os.path.join("static", "index.html"))

@app.post("/remove-bg")
async def remove_bg(file: UploadFile = File(...)):
    image_bytes = await file.read()
    output = remove_background(image_bytes)
    return Response(content=output, media_type="image/png")
