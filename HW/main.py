"""Serve the existing Bonchorok app locally through FastAPI."""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
with (DIST_DIR / "herbs.json").open(encoding="utf-8") as source:
    catalog = json.load(source)
if not isinstance(catalog, list) or not catalog:
    raise RuntimeError("dist/herbs.json must contain a non-empty herb list")

app = FastAPI(
    title="본초록 로컬 서버",
    description="한약재 정보 앱을 제공하는 FastAPI 서버의 상태 확인 API",
    version="1.0.0",
)


@app.get("/api/health", tags=["health"])
def health() -> dict:
    """Confirm that the app has started and its catalog has loaded."""
    return {"status": "ok", "service": "bonchorok", "herb_count": len(catalog)}


# Register API routes first. Only public assets, never the project root, are served.
app.mount("/", StaticFiles(directory=DIST_DIR, html=True), name="website")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
