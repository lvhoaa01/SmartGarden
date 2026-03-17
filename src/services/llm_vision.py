import asyncio
import base64
import json
from concurrent.futures import ThreadPoolExecutor
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
from core.config import config

SYSTEM_PROMPT = (
    "Bạn là AI chuyên gia nông nghiệp thông minh. "
    "Phân tích hình ảnh cây trồng kết hợp dữ liệu cảm biến, trả về JSON duy nhất:\n"
    '{"reasoning": "<giải thích ngắn gọn tình trạng cây>", "action_code": <int>}\n'
    "action_code: 0=Giữ nguyên, 1=Bật bơm, 2=Bật quạt, 3=Bơm+Quạt, 5=Bật đèn.\n"
    "Chỉ trả JSON, không viết thêm gì."
)


class QwenVLMService:
    """Singleton VLM service — chạy inference trên ThreadPoolExecutor để không block event loop."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = asyncio.Lock()
        self._llm = None
        self._load_model()

    def _load_model(self):
        try:
            chat_handler = Llava15ChatHandler(
                clip_model_path=config.models.get_clip_path()
            )
            self._llm = Llama(
                model_path=config.models.get_vlm_path(),
                chat_handler=chat_handler,
                n_ctx=2048,
                n_gpu_layers=-1,
            )
        except Exception:
            self._llm = None

    @staticmethod
    def parse_vlm_action(text: str) -> int:
        text_lower = text.lower()
        need_water = any(
            kw in text_lower
            for kw in ["bật bơm", "tưới", "thiếu nước", "khô", "tăng ẩm"]
        )
        need_cooling = any(
            kw in text_lower
            for kw in ["bật quạt", "làm mát", "giảm nhiệt", "nóng"]
        )
        need_light = any(
            kw in text_lower
            for kw in ["bật đèn", "tăng sáng", "thiếu sáng"]
        )

        if need_water and need_cooling:
            return 3
        if need_water:
            return 1
        if need_cooling:
            return 2
        if need_light:
            return 5
        return 0

    def _parse_json_response(self, raw: str) -> tuple[str, int]:
        """Cố gắng parse JSON từ output; fallback sang keyword matching."""
        try:
            data = json.loads(raw)
            reasoning = data.get("reasoning", raw)
            action_code = int(data.get("action_code", 0))
            if action_code not in (0, 1, 2, 3, 5):
                action_code = self.parse_vlm_action(reasoning)
            return reasoning, action_code
        except (json.JSONDecodeError, ValueError, TypeError):
            return raw, self.parse_vlm_action(raw)

    def _analyze_sync(
        self,
        temperature: float,
        humidity: float,
        avg_soil: float,
        light_lux: float,
        image_bytes: bytes,
    ) -> tuple[str, int]:
        if not self._llm:
            return "AI Offline", 0

        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt_text = (
            f"Dữ liệu cảm biến: Nhiệt độ={temperature}°C, "
            f"Độ ẩm KK={humidity}%, Độ ẩm đất={avg_soil}%, "
            f"Ánh sáng={light_lux} lux. "
            f"Phân tích hình ảnh và đề xuất hành động."
        )

        response = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_b64}"
                            },
                        },
                        {"type": "text", "text": prompt_text},
                    ],
                },
            ]
        )

        ai_text = response["choices"][0]["message"]["content"]
        return self._parse_json_response(ai_text)

    async def analyze(
        self,
        temperature: float,
        humidity: float,
        avg_soil: float,
        light_lux: float,
        image_bytes: bytes,
    ) -> tuple[str, int]:
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                self._analyze_sync,
                temperature,
                humidity,
                avg_soil,
                light_lux,
                image_bytes,
            )
