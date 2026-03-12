import os
import uvicorn

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 7860))
    reload = os.environ.get("RELOAD", "").lower() in {"1", "true", "yes", "on"}
    print(f"Starting server on http://{host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload
    )
