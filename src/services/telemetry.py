import json
import threading
from datetime import datetime
from pathlib import Path

import pyodbc

from core.config import config
from services.llm_vision import QwenVLMService
from services.state_manager import state_manager


class TelemetryService:
    def __init__(self, vlm_service: QwenVLMService):
        self.vlm = vlm_service
        self._jsonl_lock = threading.Lock()
        config.uploads_dir.mkdir(parents=True, exist_ok=True)
        config.dataset_dir.mkdir(parents=True, exist_ok=True)

    # ── DB helper ───────────────────────────────────────────
    def _get_conn(self) -> pyodbc.Connection:
        return pyodbc.connect(config.db.connection_string)

    # ── Lưu ảnh vật lý ─────────────────────────────────────
    @staticmethod
    def _save_image(node_id: int, image_bytes: bytes) -> str:
        """Lưu ảnh .jpg, trả về relative path (VD: uploads/node_1/20260317_143052.jpg)."""
        node_dir = config.uploads_dir / f"node_{node_id}"
        node_dir.mkdir(parents=True, exist_ok=True)
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        filepath = node_dir / filename
        filepath.write_bytes(image_bytes)
        return f"uploads/node_{node_id}/{filename}"

    # ── Append JSONL (Hybrid Labeling) ──────────────────────
    def _append_jsonl(
        self,
        node_id: int,
        image_path: str,
        sensors: dict,
        ai_reasoning: str,
        ai_action: int,
    ):
        record = {
            "timestamp": datetime.now().isoformat(),
            "node_id": node_id,
            "image_path": image_path,
            "sensors": sensors,
            "ai_reasoning": ai_reasoning,
            "ai_action": ai_action,
            "human_correction": None,
        }
        jsonl_path = config.dataset_dir / "labels.jsonl"
        with self._jsonl_lock:
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ── Pipeline chính ──────────────────────────────────────
    async def process_and_store(
        self,
        node_id: int,
        temperature: float,
        humidity: float,
        avg_soil: float,
        light_lux: float,
        image_bytes: bytes,
    ) -> dict:
        # 1. Lưu ảnh
        image_path = self._save_image(node_id, image_bytes)

        # 2. AI phân tích
        ai_reasoning, action_code = await self.vlm.analyze(
            temperature, humidity, avg_soil, light_lux, image_bytes
        )

        # 3. Ghi DB
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            # Cập nhật Node status
            cursor.execute(
                "UPDATE Nodes SET status='online', last_seen=GETDATE() WHERE id=?",
                (node_id,),
            )

            # Insert Telemetry
            cursor.execute(
                """
                INSERT INTO Telemetry (node_id, temperature, humidity, avg_soil, light_lux, image_path)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (node_id, temperature, humidity, avg_soil, light_lux, image_path),
            )
            telemetry_id = cursor.fetchone()[0]

            # Insert Action_Logs
            if action_code != 0:
                cursor.execute(
                    """
                    INSERT INTO Action_Logs (node_id, telemetry_id, action_type, triggered_by, reasoning)
                    VALUES (?, ?, ?, 'AI', ?)
                    """,
                    (node_id, telemetry_id, action_code, ai_reasoning[:500]),
                )

            conn.commit()
        finally:
            conn.close()

        # 4. Append JSONL cho fine-tune dataset
        sensors = {
            "temp": temperature,
            "hum": humidity,
            "soil": avg_soil,
            "light": light_lux,
        }
        self._append_jsonl(node_id, image_path, sensors, ai_reasoning, action_code)

        # 5. Cập nhật State Manager
        image_url = f"/{image_path}"
        node_state = await state_manager.update_telemetry(
            node_id=node_id,
            temperature=temperature,
            humidity=humidity,
            avg_soil=avg_soil,
            light_lux=light_lux,
            image_url=image_url,
            ai_reasoning=ai_reasoning,
            action_code=action_code,
        )

        return {
            "status": "success",
            "node_id": node_id,
            "ai_reasoning": ai_reasoning,
            "ai_action_code": action_code,
            "device_states": node_state.devices.to_dict(),
            "image_url": image_url,
        }

    # ── Log Manual Action ───────────────────────────────────
    async def log_manual_action(
        self, node_id: int, action_type: int, reasoning: str = "Thao tác thủ công"
    ):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO Action_Logs (node_id, telemetry_id, action_type, triggered_by, reasoning)
                VALUES (?, NULL, ?, 'MANUAL', ?)
                """,
                (node_id, action_type, reasoning),
            )
            conn.commit()
        finally:
            conn.close()

        node_state = await state_manager.set_manual_action(node_id, action_type)
        return node_state

    # ── Truy vấn lịch sử ───────────────────────────────────
    def fetch_latest(self, node_id: int = None, limit: int = 20) -> list:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            if node_id:
                cursor.execute(
                    """
                    SELECT TOP (?) t.id, t.node_id, t.temperature, t.humidity,
                           t.avg_soil, t.light_lux, t.image_path,
                           t.created_at, n.name as node_name
                    FROM Telemetry t
                    JOIN Nodes n ON t.node_id = n.id
                    WHERE t.node_id = ?
                    ORDER BY t.created_at DESC
                    """,
                    (limit, node_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT TOP (?) t.id, t.node_id, t.temperature, t.humidity,
                           t.avg_soil, t.light_lux, t.image_path,
                           t.created_at, n.name as node_name
                    FROM Telemetry t
                    JOIN Nodes n ON t.node_id = n.id
                    ORDER BY t.created_at DESC
                    """,
                    (limit,),
                )
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            data = []
            for row in rows:
                record = dict(zip(columns, row))
                if record.get("created_at"):
                    record["created_at"] = record["created_at"].isoformat()
                data.append(record)
            return data[::-1]
        finally:
            conn.close()

    def fetch_nodes(self) -> list:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, name, location, status, last_seen FROM Nodes")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            result = []
            for row in rows:
                record = dict(zip(columns, row))
                if record.get("last_seen"):
                    record["last_seen"] = record["last_seen"].isoformat()
                result.append(record)
            return result
        finally:
            conn.close()
