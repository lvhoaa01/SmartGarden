from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import AppState, create_router
from services.llm_vision import QwenVLMService
from services.telemetry import TelemetryService

app = FastAPI(title="SmartHouse Core API - Enterprise VLM Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vlm_service = QwenVLMService()
telemetry_service = TelemetryService(vlm_service)

app_state = AppState(vlm_service=vlm_service, telemetry_service=telemetry_service)
api_router = create_router(app_state)

app.include_router(api_router)