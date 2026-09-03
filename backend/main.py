"""Cookbook ASGI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.api.recipes import router as recipes_router
from backend.api.imports import router as imports_router
from backend.api.share import router as share_router


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Pi Cookbook")
app.include_router(share_router)
app.include_router(imports_router)
app.include_router(recipes_router)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
@app.get("/favicon.ico", include_in_schema=False)
def app_icon() -> RedirectResponse:
    return RedirectResponse(url="/icon.svg", status_code=307)


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")