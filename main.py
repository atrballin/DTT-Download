from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

app = FastAPI(title="DaTraders Terminal Download Page")

# Read the HTML content
html_file_path = Path(__file__).parent / "index.html"

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open(html_file_path, "r", encoding="utf-8") as f:
        return f.read()

# Optional health check endpoint, often useful for Render deployments
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
