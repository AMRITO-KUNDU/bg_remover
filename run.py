import uvicorn

if __name__ == "__main__":
    print("Starting server on http://0.0.0.0:5000")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    )
