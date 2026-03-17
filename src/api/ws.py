import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.config import config
from services.websocket_manager import ws_manager
from services.state_manager import state_manager
from services.telemetry import TelemetryService


def create_ws_router(telemetry_service: TelemetryService) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await ws_manager.connect(ws, subscribe_to="all")
        try:
            # Gửi state hiện tại ngay khi kết nối
            states = await state_manager.get_all_states()
            await ws.send_text(
                json.dumps(
                    {"type": "init_state", "data": states},
                    ensure_ascii=False,
                    default=str,
                )
            )

            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")

                # Client subscribe 1 node cụ thể
                if msg_type == "subscribe":
                    node_id = str(msg.get("node_id", "all"))
                    await ws_manager.subscribe(ws, node_id)

                # Client gửi manual action qua WS
                elif msg_type == "manual_action":
                    api_key = msg.get("api_key", "")
                    if api_key != config.api_key:
                        await ws.send_text(
                            json.dumps({"type": "error", "detail": "Invalid API Key"})
                        )
                        continue

                    node_id = msg.get("node_id")
                    action_type = msg.get("action_type", 0)
                    if action_type not in (0, 1, 2, 3, 5):
                        continue

                    node_state = await telemetry_service.log_manual_action(
                        node_id, action_type
                    )
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

                # Client đổi mode qua WS
                elif msg_type == "set_mode":
                    api_key = msg.get("api_key", "")
                    if api_key != config.api_key:
                        await ws.send_text(
                            json.dumps({"type": "error", "detail": "Invalid API Key"})
                        )
                        continue

                    node_id = msg.get("node_id")
                    mode = msg.get("mode", "auto")
                    if mode not in ("auto", "manual"):
                        continue

                    await state_manager.set_mode(node_id, mode)
                    await ws_manager.broadcast(
                        node_id,
                        {"type": "mode_update", "node_id": node_id, "mode": mode},
                    )

        except WebSocketDisconnect:
            pass
        finally:
            await ws_manager.disconnect(ws)

    return router
