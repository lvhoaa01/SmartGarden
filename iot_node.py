import time
import requests
import cv2
import board
import busio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import smbus2
import RPi.GPIO as GPIO

API_URL = "http://YOUR_SERVER_IP:8000/api/telemetry_with_image"
BATCH_ID = "GREENHOUSE_ZONE_1"
SLEEP_TIME = 600

RELAY_PUMP_PIN = 17
RELAY_FAN_PIN = 27
RELAY_LIGHT_PIN = 22

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PUMP_PIN, GPIO.OUT)
GPIO.setup(RELAY_FAN_PIN, GPIO.OUT)
GPIO.setup(RELAY_LIGHT_PIN, GPIO.OUT)
GPIO.output(RELAY_PUMP_PIN, GPIO.LOW)
GPIO.output(RELAY_FAN_PIN, GPIO.LOW)
GPIO.output(RELAY_LIGHT_PIN, GPIO.LOW)

camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

dht_device = adafruit_dht.DHT22(board.D4)
i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS.ADS1115(i2c)
soil_channel = AnalogIn(ads, ADS.P0)
co2_channel = AnalogIn(ads, ADS.P1)

bus = smbus2.SMBus(1)
BH1750_ADDR = 0x23

def read_light_bh1750():
    try:
        data = bus.read_i2c_block_data(BH1750_ADDR, 0x20, 2)
        lux = (data[0] << 8 | data[1]) / 1.2
        return round(lux, 1)
    except Exception:
        return None

def read_real_sensors():
    temp = hum = soil = light = co2 = None
    try:
        temp = round(dht_device.temperature, 1)
        hum = round(dht_device.humidity, 1)
    except Exception:
        pass
    try:
        voltage = soil_channel.voltage
        soil_pct = ((3.3 - voltage) / (3.3 - 1.5)) * 100
        soil = round(max(0.0, min(100.0, soil_pct)), 1)
    except Exception:
        pass
    try:
        co2_voltage = co2_channel.voltage
        co2 = round((co2_voltage / 3.3) * 1000 + 400, 1)
    except Exception:
        pass
    light = read_light_bh1750()
    return temp, hum, soil, light, co2

def capture_real_image():
    for _ in range(3): camera.read()
    ret, frame = camera.read()
    if not ret: return None
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
    result, encimg = cv2.imencode('.jpg', frame, encode_param)
    return encimg.tobytes()

try:
    while True:
        t, h, s, l, c = read_real_sensors()
        img_bytes = capture_real_image()

        if t is not None and h is not None and img_bytes is not None:
            data_payload = {
                "batch_id": BATCH_ID,
                "temperature": t,
                "humidity": h,
                "avg_soil": s if s is not None else 0.0,
                "light_lux": l if l is not None else 0.0,
                "co2_level": c if c is not None else 0.0
            }
            files_payload = {
                "image_file": ("rasp_capture.jpg", img_bytes, "image/jpeg")
            }

            try:
                res = requests.post(API_URL, data=data_payload, files=files_payload, timeout=20)
                response_data = res.json()
                action_code = response_data.get("ai_action_code", 0)

                GPIO.output(RELAY_PUMP_PIN, GPIO.LOW)
                GPIO.output(RELAY_FAN_PIN, GPIO.LOW)
                GPIO.output(RELAY_LIGHT_PIN, GPIO.LOW)

                if action_code == 1:
                    GPIO.output(RELAY_PUMP_PIN, GPIO.HIGH)
                elif action_code == 2:
                    GPIO.output(RELAY_FAN_PIN, GPIO.HIGH)
                elif action_code == 3:
                    GPIO.output(RELAY_PUMP_PIN, GPIO.HIGH)
                    GPIO.output(RELAY_FAN_PIN, GPIO.HIGH)
                elif action_code == 5:
                    GPIO.output(RELAY_LIGHT_PIN, GPIO.HIGH)

            except requests.exceptions.RequestException:
                if s is not None and s < 40.0:
                    GPIO.output(RELAY_PUMP_PIN, GPIO.HIGH)
                    time.sleep(10)
                    GPIO.output(RELAY_PUMP_PIN, GPIO.LOW)

        time.sleep(SLEEP_TIME)

except KeyboardInterrupt:
    pass
finally:
    GPIO.cleanup()
    camera.release()