from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from api.dependencies import verify_api_key
from services.telemetry import TelemetryService
from services.state_manager import state_manager
from services.websocket_manager import ws_manager


def create_router(telemetry_service: TelemetryService) -> APIRouter:
    router = APIRouter(prefix="/api", dependencies=[Depends(verify_api_key)])

    # ── Nhận data + ảnh từ Edge Node ────────────────────────
    @router.post("/telemetry")
    async def receive_telemetry(
        node_id: int = Form(...),
        temperature: float = Form(...),
        humidity: float = Form(...),
        avg_soil: float = Form(...),
        light_lux: float = Form(...),
        image_file: UploadFile = File(...),
    ):
        image_bytes = await image_file.read()
        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")

        result = await telemetry_service.process_and_store(
            node_id, temperature, humidity, avg_soil, light_lux, image_bytes
        )

        # Broadcast real-time qua WebSocket
        await ws_manager.broadcast(
            node_id,
            {
                "type": "telemetry_update",
                "node_id": node_id,
                "data": {
                    "temperature": temperature,
                    "humidity": humidity,
                    "avg_soil": avg_soil,
                    "light_lux": light_lux,
                    "image_url": result.get("image_url"),
                    "ai_reasoning": result.get("ai_reasoning"),
                    "action_code": result.get("ai_action_code"),
                    "device_states": result.get("device_states"),
                    "created_at": None,
                },
            },
        )
        return result

    # ── Manual action từ UI ─────────────────────────────────
    @router.post("/action")
    async def manual_action(
        node_id: int = Form(...),
        action_type: int = Form(...),
    ):
        if action_type not in (0, 1, 2, 3, 5):
            raise HTTPException(status_code=400, detail="Invalid action_type")

        node_state = await telemetry_service.log_manual_action(node_id, action_type)
        await ws_manager.broadcast(
            node_id,
            {
                "type": "device_update",
                "node_id": node_id,
                "device_states": node_state.devices.to_dict(),
                "action_code": action_type,
                "triggered_by": "MANUAL",
            },
        )
        return {
            "status": "success",
            "node_id": node_id,
            "action_type": action_type,
            "device_states": node_state.devices.to_dict(),
        }

    # ── Đổi chế độ Auto/Manual ──────────────────────────────
    @router.post("/mode")
    async def set_mode(
        node_id: int = Form(...),
        mode: str = Form(...),
    ):
        if mode not in ("auto", "manual"):
            raise HTTPException(status_code=400, detail="Mode must be 'auto' or 'manual'")
        node_state = await state_manager.set_mode(node_id, mode)
        await ws_manager.broadcast(
            node_id,
            {
                "type": "mode_update",
                "node_id": node_id,
                "mode": mode,
            },
        )
        return {"status": "success", "node_id": node_id, "mode": mode}

    # ── Lấy lịch sử Telemetry ──────────────────────────────
    @router.get("/telemetry/latest")
    async def get_latest(node_id: int = None, limit: int = 20):
        data = telemetry_service.fetch_latest(node_id=node_id, limit=limit)
        return {"status": "success", "data": data}

    # ── Lấy danh sách Nodes ─────────────────────────────────
    @router.get("/nodes")
    async def get_nodes():
        nodes = telemetry_service.fetch_nodes()
        return {"status": "success", "data": nodes}

    # ── Lấy state hiện tại (in-memory) ──────────────────────
    @router.get("/state")
    async def get_state(node_id: int = None):
        if node_id:
            state = await state_manager.get_state(node_id)
            return {"status": "success", "data": state}
        states = await state_manager.get_all_states()
        return {"status": "success", "data": states}

    return router
