"""
SmartGarden — Edge Node (Raspberry Pi / Laptop Mock)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Adapter Pattern cho cảm biến + Camera.
USE_MOCK_HARDWARE = True → chạy trên laptop không cần phần cứng.
Retry khi mất mạng, tự tắt relay nếu mất kết nối > 5 phút.
"""

import io
import os
import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from datetime import datetime

# ══════════════════════════════════════════════════════
# CẤU HÌNH
# ══════════════════════════════════════════════════════
USE_MOCK_HARDWARE = True          # True = test trên laptop; False = Raspberry Pi thật
SERVER_URL = "http://localhost:8000"
API_KEY = "smartgarden-secret-key-2026"
NODE_ID = 1
SLEEP_TIME = 30                   # Giây giữa 2 lần gửi
MAX_RETRIES = 5                   # Số lần retry khi lỗi mạng
RETRY_DELAY = 3                   # Giây chờ giữa các lần retry
OFFLINE_TIMEOUT = 300             # 5 phút → tự tắt relay

RELAY_PUMP_PIN = 17
RELAY_FAN_PIN = 27
RELAY_LIGHT_PIN = 22

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("EdgeNode")


# ══════════════════════════════════════════════════════
# ADAPTER PATTERN — Cảm biến
# ══════════════════════════════════════════════════════
class SensorAdapter(ABC):
    @abstractmethod
    def read(self) -> dict:
        """Trả về dict: {temperature, humidity, avg_soil, light_lux}"""
        ...

class CameraAdapter(ABC):
    @abstractmethod
    def capture(self) -> bytes:
        """Trả về image bytes (JPEG)."""
        ...

class RelayAdapter(ABC):
    @abstractmethod
    def set_state(self, pump: bool, fan: bool, light: bool): ...
    @abstractmethod
    def all_off(self): ...
    @abstractmethod
    def cleanup(self): ...


# ── Mock Implementations ────────────────────────────
class MockSensor(SensorAdapter):
    def read(self) -> dict:
        return {
            "temperature": round(random.uniform(25.0, 38.0), 1),
            "humidity": round(random.uniform(40.0, 90.0), 1),
            "avg_soil": round(random.uniform(15.0, 85.0), 1),
            "light_lux": round(random.uniform(200.0, 5000.0), 1),
        }

class MockCamera(CameraAdapter):
    def capture(self) -> bytes:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            # Fallback: tạo JPEG tối thiểu bằng bytes
            return self._minimal_jpeg()

        img = Image.new("RGB", (640, 480), color=(200, 220, 200))
        draw = ImageDraw.Draw(img)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        draw.text((30, 30), f"MOCK CAMERA — Node {NODE_ID}", fill=(50, 50, 50))
        draw.text((30, 60), f"Captured: {ts}", fill=(80, 80, 80))
        draw.text((30, 100), "SmartGarden Edge Node", fill=(0, 100, 0))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return buf.getvalue()

    @staticmethod
    def _minimal_jpeg() -> bytes:
        # 1x1 white pixel JPEG
        return (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00'
            b'\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b'
            b'\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04'
            b'\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07'
            b'\x22q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16'
            b'\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz'
            b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99'
            b'\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7'
            b'\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5'
            b'\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1'
            b'\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa'
            b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00T\xdb\xa8\xa0\x02\x80\x0f\xff\xd9'
        )

class MockRelay(RelayAdapter):
    def __init__(self):
        self.pump = False
        self.fan = False
        self.light = False

    def set_state(self, pump: bool, fan: bool, light: bool):
        self.pump, self.fan, self.light = pump, fan, light
        states = []
        if pump: states.append("BƠM")
        if fan: states.append("QUẠT")
        if light: states.append("ĐÈN")
        log.info(f"[MOCK RELAY] {'  '.join(states) if states else 'TẤT CẢ TẮT'}")

    def all_off(self):
        self.set_state(False, False, False)

    def cleanup(self):
        self.all_off()
        log.info("[MOCK RELAY] Cleanup done.")


# ── Real Hardware (Raspberry Pi) ────────────────────
class RealSensor(SensorAdapter):
    def __init__(self):
        import board, busio
        import adafruit_dht
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        import smbus2

        self.dht = adafruit_dht.DHT22(board.D4)
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        self.soil_ch = AnalogIn(ads, ADS.P0)
        self.bus = smbus2.SMBus(1)
        self.BH1750_ADDR = 0x23

    def read(self) -> dict:
        temp = hum = soil = light = None
        try:
            temp = round(self.dht.temperature, 1)
            hum = round(self.dht.humidity, 1)
        except Exception:
            pass
        try:
            v = self.soil_ch.voltage
            soil = round(max(0.0, min(100.0, ((3.3 - v) / (3.3 - 1.5)) * 100)), 1)
        except Exception:
            pass
        try:
            data = self.bus.read_i2c_block_data(self.BH1750_ADDR, 0x20, 2)
            light = round((data[0] << 8 | data[1]) / 1.2, 1)
        except Exception:
            pass
        return {
            "temperature": temp if temp is not None else 0.0,
            "humidity": hum if hum is not None else 0.0,
            "avg_soil": soil if soil is not None else 0.0,
            "light_lux": light if light is not None else 0.0,
        }

class RealCamera(CameraAdapter):
    def __init__(self):
        import cv2
        self.cv2 = cv2
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def capture(self) -> bytes:
        for _ in range(3):
            self.cap.read()
        ret, frame = self.cap.read()
        if not ret:
            return b""
        _, buf = self.cv2.imencode(".jpg", frame, [int(self.cv2.IMWRITE_JPEG_QUALITY), 80])
        return buf.tobytes()

    def release(self):
        self.cap.release()

class RealRelay(RelayAdapter):
    def __init__(self):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        for pin in (RELAY_PUMP_PIN, RELAY_FAN_PIN, RELAY_LIGHT_PIN):
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

    def set_state(self, pump: bool, fan: bool, light: bool):
        self.GPIO.output(RELAY_PUMP_PIN, self.GPIO.HIGH if pump else self.GPIO.LOW)
        self.GPIO.output(RELAY_FAN_PIN, self.GPIO.HIGH if fan else self.GPIO.LOW)
        self.GPIO.output(RELAY_LIGHT_PIN, self.GPIO.HIGH if light else self.GPIO.LOW)

    def all_off(self):
        self.set_state(False, False, False)

    def cleanup(self):
        self.all_off()
        self.GPIO.cleanup()


# ══════════════════════════════════════════════════════
# EDGE NODE MAIN LOOP
# ══════════════════════════════════════════════════════
def send_with_retry(sensor_data: dict, image_bytes: bytes) -> dict | None:
    """Gửi data lên server với retry. Trả về response dict hoặc None."""
    url = f"{SERVER_URL}/api/telemetry"
    headers = {"X-API-Key": API_KEY}

    form_data = {
        "node_id": str(NODE_ID),
        "temperature": str(sensor_data["temperature"]),
        "humidity": str(sensor_data["humidity"]),
        "avg_soil": str(sensor_data["avg_soil"]),
        "light_lux": str(sensor_data["light_lux"]),
    }
    files = {"image_file": ("capture.jpg", image_bytes, "image/jpeg")}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url, data=form_data, files=files, headers=headers, timeout=20
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            log.warning(f"Retry {attempt}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    return None


def apply_action(relay: RelayAdapter, action_code: int):
    pump = action_code in (1, 3)
    fan = action_code in (2, 3)
    light = action_code == 5
    relay.set_state(pump, fan, light)


def main():
    log.info(f"Edge Node khởi động — Mock={USE_MOCK_HARDWARE}, Node ID={NODE_ID}")

    # Khởi tạo adapters
    if USE_MOCK_HARDWARE:
        sensor: SensorAdapter = MockSensor()
        camera: CameraAdapter = MockCamera()
        relay: RelayAdapter = MockRelay()
    else:
        sensor = RealSensor()
        camera = RealCamera()
        relay = RealRelay()

    last_success_time = time.time()

    try:
        while True:
            # 1. Đọc cảm biến + chụp ảnh
            data = sensor.read()
            image_bytes = camera.capture()
            log.info(
                f"Sensors → T={data['temperature']}°C, H={data['humidity']}%, "
                f"Soil={data['avg_soil']}%, Light={data['light_lux']} lux"
            )

            if not image_bytes:
                log.error("Không chụp được ảnh, bỏ qua chu kỳ này.")
                time.sleep(SLEEP_TIME)
                continue

            # 2. Gửi lên server (có retry)
            result = send_with_retry(data, image_bytes)

            if result is not None:
                last_success_time = time.time()
                action_code = result.get("ai_action_code", 0)
                reasoning = result.get("ai_reasoning", "")
                log.info(f"AI → action={action_code}: {reasoning[:120]}")
                apply_action(relay, action_code)
            else:
                # Không gửi được → kiểm tra thời gian offline
                elapsed = time.time() - last_success_time
                log.error(f"Gửi thất bại. Offline {elapsed:.0f}s/{OFFLINE_TIMEOUT}s")

                if elapsed >= OFFLINE_TIMEOUT:
                    log.critical(
                        "MẤT KẾT NỐI > 5 PHÚT → TỰ TẮT TẤT CẢ RELAY ĐỂ AN TOÀN!"
                    )
                    relay.all_off()

            # 3. Chờ chu kỳ tiếp theo
            time.sleep(SLEEP_TIME)

    except KeyboardInterrupt:
        log.info("Dừng bởi người dùng.")
    finally:
        relay.cleanup()
        if not USE_MOCK_HARDWARE and hasattr(camera, "release"):
            camera.release()
        log.info("Edge Node đã tắt.")


if __name__ == "__main__":
    main()
