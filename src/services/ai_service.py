import base64
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Llava15ChatHandler
from core.config import MODEL_PATH, CLIP_PATH

try:
    chat_handler = Llava15ChatHandler(clip_model_path=CLIP_PATH)
    vlm_model = Llama(
        model_path=MODEL_PATH,
        chat_handler=chat_handler,
        n_ctx=2048,
        n_gpu_layers=-1
    )
except Exception:
    vlm_model = None

def parse_vlm_action(vlm_response_text: str) -> int:
    text = vlm_response_text.lower()
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

def analyze_environment_and_image(temperature: float, humidity: float, avg_soil: float, light_lux: float, image_bytes: bytes) -> tuple:
    if not vlm_model:
        return "AI Offline", 0
        
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')
    prompt_text = f"Nhiet do: {temperature}C, Do am KK: {humidity}%, Dat: {avg_soil}%, Anh sang: {light_lux} lux. Tinh trang cay va de xuat?"
    
    response = vlm_model.create_chat_completion(
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
    action_code = parse_vlm_action(ai_text)
    
    return ai_text, action_code

    #Propmt engineering: Khiến cho đầu ra trả về là 1 file json có 2 trường: "reasoning" và "action_code". Trong đó "reasoning" là phần giải thích của AI về tình trạng cây trồng dựa trên dữ liệu cảm biến và hình ảnh. "action_code" là mã số hành động mà AI đề xuất (1: bật bơm, 2: bật quạt, 3: bật bơm + quạt, 5: bật đèn).