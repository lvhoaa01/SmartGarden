import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class DeviceStates:
    pump: bool = False
    fan: bool = False
    light: bool = False

    def to_dict(self) -> dict:
        return {"pump": self.pump, "fan": self.fan, "light": self.light}

    def apply_action_code(self, code: int):
        """Áp dụng action_code từ AI: 0=giữ nguyên tắt, 1=bơm, 2=quạt, 3=bơm+quạt, 5=đèn."""
        self.pump = code in (1, 3)
        self.fan = code in (2, 3)
        self.light = code == 5


@dataclass
class NodeState:
    node_id: int
    status: str = "offline"
    last_seen: Optional[datetime] = None
    temperature: float = 0.0
    humidity: float = 0.0
    avg_soil: float = 0.0
    light_lux: float = 0.0
    image_url: Optional[str] = None
    ai_reasoning: str = ""
    action_code: int = 0
    mode: str = "auto"  # 'auto' | 'manual'
    devices: DeviceStates = field(default_factory=DeviceStates)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "avg_soil": self.avg_soil,
            "light_lux": self.light_lux,
            "image_url": self.image_url,
            "ai_reasoning": self.ai_reasoning,
            "action_code": self.action_code,
            "mode": self.mode,
            "device_states": self.devices.to_dict(),
        }


class StateManager:
    """In-memory state cho tất cả Nodes. Thread-safe qua asyncio.Lock()."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._nodes: Dict[int, NodeState] = {}

    async def get_or_create(self, node_id: int) -> NodeState:
        async with self._lock:
            if node_id not in self._nodes:
                self._nodes[node_id] = NodeState(node_id=node_id)
            return self._nodes[node_id]

    async def update_telemetry(
        self,
        node_id: int,
        temperature: float,
        humidity: float,
        avg_soil: float,
        light_lux: float,
        image_url: Optional[str],
        ai_reasoning: str,
        action_code: int,
    ) -> NodeState:
        async with self._lock:
            state = self._nodes.setdefault(node_id, NodeState(node_id=node_id))
            state.status = "online"
            state.last_seen = datetime.now()
            state.temperature = temperature
            state.humidity = humidity
            state.avg_soil = avg_soil
            state.light_lux = light_lux
            state.image_url = image_url
            state.ai_reasoning = ai_reasoning
            state.action_code = action_code
            if state.mode == "auto":
                state.devices.apply_action_code(action_code)
            return state

    async def set_manual_action(self, node_id: int, action_type: int) -> NodeState:
        async with self._lock:
            state = self._nodes.setdefault(node_id, NodeState(node_id=node_id))
            state.mode = "manual"
            state.devices.apply_action_code(action_type)
            return state

    async def set_mode(self, node_id: int, mode: str) -> NodeState:
        async with self._lock:
            state = self._nodes.setdefault(node_id, NodeState(node_id=node_id))
            state.mode = mode
            return state

    async def set_node_offline(self, node_id: int):
        async with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].status = "offline"

    async def get_all_states(self) -> list:
        async with self._lock:
            return [s.to_dict() for s in self._nodes.values()]

    async def get_state(self, node_id: int) -> Optional[dict]:
        async with self._lock:
            state = self._nodes.get(node_id)
            return state.to_dict() if state else None


state_manager = StateManager()
