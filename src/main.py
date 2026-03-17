import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import config
from services.llm_vision import QwenVLMService
from services.telemetry import TelemetryService
from api.routes import create_router
from api.ws import create_ws_router

# ── Khởi tạo App ────────────────────────────────────────────
app = FastAPI(title="SmartGarden API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Service layer (Singleton VLM) ───────────────────────────
vlm_service = QwenVLMService()
telemetry_service = TelemetryService(vlm_service)

# ── REST API + WebSocket ────────────────────────────────────
app.include_router(create_router(telemetry_service))
app.include_router(create_ws_router(telemetry_service))

# ── Static files: Web UI + uploaded images ──────────────────
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

uploads_dir = config.uploads_dir
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/")
async def root():
    """Redirect đến Web UI."""
    from fastapi.responses import FileResponse

    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "SmartGarden API is running. Put index.html in src/static/"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=config.host, port=config.port, reload=True)
