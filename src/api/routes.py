from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from services.telemetry_service import process_and_store_telemetry, fetch_latest_telemetry

router = APIRouter()

@router.post("/api/telemetry_with_image")
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
        result = process_and_store_telemetry(
            batch_id, temperature, humidity, avg_soil, light_lux, co2_level, image_bytes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/telemetry/latest")
async def get_latest_data(limit: int = 20):
    try:
        data = fetch_latest_telemetry(limit)
        return {"status": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))