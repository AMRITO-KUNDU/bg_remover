import os
import uvicorn

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on http://{host}:{port}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True
    )
