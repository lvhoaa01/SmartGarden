import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
from core.config import config

class QwenVLMService:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = asyncio.Lock()
        self._llm = None
        self._load_model()

    def _load_model(self):
        if self._llm is not None:
            return
        try:
            chat_handler = Llava15ChatHandler(clip_model_path=config.models.get_clip_path())
            self._llm = Llama(
                model_path=config.models.get_vlm_path(),
                chat_handler=chat_handler,
                n_ctx=2048,
                n_gpu_layers=-1
            )
        except Exception:
            self._llm = None

    def parse_vlm_action(self, text: str) -> int:
        text = text.lower()
        action_code = 0
        
        need_water = any(kw in text for kw in ["bật bơm", "tưới", "thiếu nước", "khô", "tăng ẩm"])
        need_cooling = any(kw in text for kw in ["bật quạt", "làm mát", "giảm nhiệt", "nóng"])
        need_light = any(kw in text for kw in ["bật đèn", "tăng sáng", "thiếu sáng"])
        
        if need_water and need_cooling:
            action_code = 3
        elif need_water:
            action_code = 1
        elif need_cooling:
            action_code = 2
        elif need_light:
            action_code = 5
                
        return action_code

    def _analyze_sync(self, temperature: float, humidity: float, avg_soil: float, light_lux: float, image_bytes: bytes) -> tuple:
        if not self._llm:
            return "AI Offline", 0

        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        prompt_text = f"Nhiet do: {temperature}C, Do am KK: {humidity}%, Dat: {avg_soil}%, Anh sang: {light_lux} lux. Tinh trang cay va de xuat?"

        response = self._llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                        {"type": "text", "text": prompt_text}
                    ]
                }
            ]
        )
        
        ai_text = response["choices"][0]["message"]["content"]
        action_code = self.parse_vlm_action(ai_text)
        
        return ai_text, action_code

    async def analyze(self, temperature: float, humidity: float, avg_soil: float, light_lux: float, image_bytes: bytes) -> tuple:
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._executor,
                self._analyze_sync,
                temperature,
                humidity,
                avg_soil,
                light_lux,
                image_bytes
            )