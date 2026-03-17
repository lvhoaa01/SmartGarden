from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from services.telemetry import TelemetryService
from services.llm_vision import QwenVLMService

class AppState:
    def __init__(self, vlm_service: QwenVLMService, telemetry_service: TelemetryService):
        self.vlm_service = vlm_service
        self.telemetry_service = telemetry_service

def create_router(state: AppState) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/telemetry_with_image")
    async def receive_multimodal_data(
        batch_id: str = Form(...),
        temperature: float = Form(...),
        humidity: float = Form(...),
        avg_soil: float = Form(...),
        light_lux: float = Form(...),    
        co2_level: float = Form(...),    
        image_file: UploadFile = File(...)
    ):
        try:
            image_bytes = await image_file.read()
            result = await state.telemetry_service.process_and_store(
                batch_id, temperature, humidity, avg_soil, light_lux, co2_level, image_bytes
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/telemetry/latest")
    async def get_latest_data(limit: int = 20):
        try:
            data = state.telemetry_service.fetch_latest(limit)
            return {"status": "success", "data": data}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router