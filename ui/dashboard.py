import sys
import json
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QTextEdit, QFrame, QGridLayout, QPushButton,
    QRadioButton, QButtonGroup, QComboBox,
)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QImage

import websocket  # websocket-client
import requests

# ── Cấu hình ────────────────────────────────────────
SERVER_HOST = "localhost"
SERVER_PORT = 8000
API_KEY = "smartgarden-secret-key-2026"
WS_URL = f"ws://{SERVER_HOST}:{SERVER_PORT}/ws"


# ══════════════════════════════════════════════════════
# WebSocket Thread — chạy nền, emit signal về main thread
# ══════════════════════════════════════════════════════
class WSThread(QThread):
    message_received = pyqtSignal(dict)
    connection_status = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        while self._running:
            try:
                self.ws = websocket.WebSocketApp(
                    WS_URL,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_close=self._on_close,
                    on_error=self._on_error,
                )
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception:
                pass
            if self._running:
                self.connection_status.emit(False)
                import time
                time.sleep(3)

    def _on_open(self, ws):
        self.connection_status.emit(True)
        ws.send(json.dumps({"type": "subscribe", "node_id": "all"}))

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            self.message_received.emit(data)
        except json.JSONDecodeError:
            pass

    def _on_close(self, ws, close_status_code, close_msg):
        self.connection_status.emit(False)

    def _on_error(self, ws, error):
        pass

    def send(self, data: dict):
        try:
            self.ws.send(json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

    def stop(self):
        self._running = False
        try:
            self.ws.close()
        except Exception:
            pass


# ══════════════════════════════════════════════════════
# Main Dashboard Window
# ══════════════════════════════════════════════════════
class SmartGardenDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartGarden — Desktop Dashboard")
        self.setGeometry(50, 50, 1366, 768)
        self._apply_light_theme()

        self.is_auto_mode = True
        self.current_node_id = 1
        self.pump_state = False
        self.fan_state = False
        self.light_state = False

        self._build_ui()
        self._start_ws()

    # ── Theme ───────────────────────────────────────
    def _apply_light_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F5F7FA; }
            QLabel { color: #2D3748; font-family: 'Segoe UI', Arial; }
            QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }
            QProgressBar { border: 1px solid #E2E8F0; border-radius: 6px; text-align: center;
                           color: #2D3748; font-weight: bold; background-color: #EDF2F7; }
            QProgressBar::chunk { background-color: #48BB78; border-radius: 5px; }
            QTextEdit { background-color: #F8FAFC; color: #4A5568; font-family: 'Segoe UI';
                        font-size: 14px; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }
            QPushButton { font-family: 'Segoe UI'; font-weight: bold; font-size: 14px;
                          border-radius: 8px; padding: 10px; color: white; }
            QRadioButton { font-family: 'Segoe UI'; font-size: 15px; font-weight: bold; color: #2D3748; }
            QRadioButton::indicator { width: 18px; height: 18px; }
            QComboBox { font-family: 'Segoe UI'; font-size: 14px; padding: 5px; border: 1px solid #E2E8F0; border-radius: 6px; }
        """)

    # ── Build UI ────────────────────────────────────
    def _build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root = QVBoxLayout(main_widget)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(20)

        title_font = QFont("Segoe UI", 13, QFont.Bold)
        value_font = QFont("Segoe UI", 28, QFont.Bold)

        # ── Top Bar ─────────────────────────────────
        top = QFrame()
        top.setFixedHeight(70)
        top.setStyleSheet("background-color: #FFFFFF; border: none; border-bottom: 2px solid #E2E8F0; border-radius: 0;")
        top_lay = QHBoxLayout(top)

        lbl_name = QLabel("🌱 SmartGarden")
        lbl_name.setFont(QFont("Segoe UI", 22, QFont.Bold))
        lbl_name.setStyleSheet("color: #3182CE; border: none;")
        top_lay.addWidget(lbl_name)
        top_lay.addStretch()

        self.lbl_ws_status = QLabel("● OFFLINE")
        self.lbl_ws_status.setStyleSheet("border: none; color: #A0AEC0; font-size: 14px; font-weight: bold;")
        top_lay.addWidget(self.lbl_ws_status)

        top_lay.addSpacing(20)
        self.mode_group = QButtonGroup(self)
        self.rb_auto = QRadioButton("TỰ ĐỘNG")
        self.rb_manual = QRadioButton("THỦ CÔNG")
        self.rb_auto.setChecked(True)
        self.rb_auto.setStyleSheet("border: none;")
        self.rb_manual.setStyleSheet("border: none;")
        self.mode_group.addButton(self.rb_auto)
        self.mode_group.addButton(self.rb_manual)
        self.rb_auto.toggled.connect(self._on_mode_toggle)
        top_lay.addWidget(self.rb_auto)
        top_lay.addWidget(self.rb_manual)

        root.addWidget(top)

        # ── Content 3 columns ───────────────────────
        content = QHBoxLayout()
        root.addLayout(content)
        col_left = QVBoxLayout()
        col_mid = QVBoxLayout()
        col_right = QVBoxLayout()
        content.addLayout(col_left, 3)
        content.addLayout(col_mid, 3)
        content.addLayout(col_right, 4)

        # ── COL LEFT: Camera ────────────────────────
        cam_frame = QFrame()
        cam_lay = QVBoxLayout(cam_frame)
        col_left.addWidget(cam_frame, 4)

        lbl_cam = QLabel("CAMERA GIÁM SÁT")
        lbl_cam.setFont(title_font)
        lbl_cam.setStyleSheet("color: #718096; border: none;")
        cam_lay.addWidget(lbl_cam)

        self.lbl_image = QLabel("Chưa có ảnh")
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setStyleSheet("border: 2px dashed #CBD5E0; background-color: #F7FAFC; border-radius: 8px; min-height: 240px;")
        cam_lay.addWidget(self.lbl_image)

        # ── COL MID: Sensors ────────────────────────
        sensor_frame = QFrame()
        sensor_lay = QGridLayout(sensor_frame)
        sensor_lay.setSpacing(15)
        col_mid.addWidget(sensor_frame)

        lbl_sensor = QLabel("THÔNG SỐ MÔI TRƯỜNG")
        lbl_sensor.setFont(title_font)
        lbl_sensor.setStyleSheet("color: #718096; border: none;")
        lbl_sensor.setAlignment(Qt.AlignCenter)
        sensor_lay.addWidget(lbl_sensor, 0, 0, 1, 2)

        def add_sensor_row(row, label_text, color):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"border: none; font-size: 15px; color: #4A5568;")
            val = QLabel("--")
            val.setFont(value_font)
            val.setStyleSheet(f"border: none; color: {color};")
            sensor_lay.addWidget(lbl, row, 0)
            sensor_lay.addWidget(val, row, 1)
            return val

        self.lbl_temp = add_sensor_row(1, "Nhiệt độ:", "#E53E3E")
        self.lbl_hum = add_sensor_row(2, "Độ ẩm KK:", "#3182CE")

        lbl_s = QLabel("Độ ẩm Đất:")
        lbl_s.setStyleSheet("border: none; font-size: 15px; color: #4A5568;")
        self.pb_soil = QProgressBar()
        self.pb_soil.setRange(0, 100)
        self.pb_soil.setValue(0)
        self.pb_soil.setFixedHeight(30)
        sensor_lay.addWidget(lbl_s, 3, 0)
        sensor_lay.addWidget(self.pb_soil, 3, 1)

        self.lbl_light = add_sensor_row(4, "Ánh sáng:", "#D69E2E")

        # ── COL RIGHT: AI Log + Device Buttons ──────
        ai_frame = QFrame()
        ai_lay = QVBoxLayout(ai_frame)
        col_right.addWidget(ai_frame, 3)

        lbl_ai = QLabel("AI QWEN VLM — SUY LUẬN")
        lbl_ai.setFont(title_font)
        lbl_ai.setStyleSheet("color: #718096; border: none;")
        ai_lay.addWidget(lbl_ai)

        self.txt_ai_log = QTextEdit()
        self.txt_ai_log.setReadOnly(True)
        ai_lay.addWidget(self.txt_ai_log)

        action_frame = QFrame()
        action_lay = QVBoxLayout(action_frame)
        col_right.addWidget(action_frame, 2)

        lbl_action = QLabel("ĐIỀU KHIỂN THIẾT BỊ")
        lbl_action.setFont(title_font)
        lbl_action.setStyleSheet("color: #718096; border: none;")
        lbl_action.setAlignment(Qt.AlignCenter)
        action_lay.addWidget(lbl_action)

        self.btn_pump = QPushButton("BƠM NƯỚC: TẮT")
        self.btn_fan = QPushButton("QUẠT GIÓ: TẮT")
        self.btn_light = QPushButton("ĐÈN: TẮT")
        for btn in (self.btn_pump, self.btn_fan, self.btn_light):
            btn.setFixedHeight(45)
            action_lay.addWidget(btn)

        self.btn_pump.clicked.connect(lambda: self._toggle_device("pump"))
        self.btn_fan.clicked.connect(lambda: self._toggle_device("fan"))
        self.btn_light.clicked.connect(lambda: self._toggle_device("light"))

        self._update_device_ui()

    # ── WebSocket ───────────────────────────────────
    def _start_ws(self):
        self.ws_thread = WSThread()
        self.ws_thread.message_received.connect(self._on_ws_message)
        self.ws_thread.connection_status.connect(self._on_ws_status)
        self.ws_thread.start()

    def _on_ws_status(self, connected: bool):
        if connected:
            self.lbl_ws_status.setText("● ONLINE")
            self.lbl_ws_status.setStyleSheet("border: none; color: #48BB78; font-size: 14px; font-weight: bold;")
        else:
            self.lbl_ws_status.setText("● OFFLINE")
            self.lbl_ws_status.setStyleSheet("border: none; color: #E53E3E; font-size: 14px; font-weight: bold;")

    def _on_ws_message(self, msg: dict):
        msg_type = msg.get("type")

        if msg_type == "init_state":
            data_list = msg.get("data", [])
            if data_list:
                self._apply_state(data_list[0])

        elif msg_type == "telemetry_update":
            data = msg.get("data", {})
            self._update_sensors(data)
            self._update_image_from_url(data.get("image_url"))
            self._append_ai_log(data.get("ai_reasoning"), data.get("action_code"))
            if data.get("device_states"):
                self._apply_device_states(data["device_states"])

        elif msg_type == "device_update":
            if msg.get("device_states"):
                self._apply_device_states(msg["device_states"])

        elif msg_type == "mode_update":
            mode = msg.get("mode", "auto")
            if mode == "auto":
                self.rb_auto.setChecked(True)
            else:
                self.rb_manual.setChecked(True)

    # ── Helpers ─────────────────────────────────────
    def _apply_state(self, state: dict):
        self.lbl_temp.setText(f'{state.get("temperature", "--")} °C')
        self.lbl_hum.setText(f'{state.get("humidity", "--")} %')
        self.pb_soil.setValue(int(state.get("avg_soil", 0)))
        self.lbl_light.setText(f'{state.get("light_lux", "--")} Lux')
        if state.get("image_url"):
            self._update_image_from_url(state["image_url"])
        if state.get("ai_reasoning"):
            self._append_ai_log(state["ai_reasoning"], state.get("action_code", 0))
        ds = state.get("device_states", {})
        if ds:
            self._apply_device_states(ds)

    def _update_sensors(self, data: dict):
        self.lbl_temp.setText(f'{data.get("temperature", "--")} °C')
        self.lbl_hum.setText(f'{data.get("humidity", "--")} %')
        self.pb_soil.setValue(int(data.get("avg_soil", 0)))
        self.lbl_light.setText(f'{data.get("light_lux", "--")} Lux')

    def _update_image_from_url(self, url: str):
        if not url:
            return
        try:
            full_url = f"http://{SERVER_HOST}:{SERVER_PORT}{url}"
            resp = requests.get(full_url, timeout=5)
            if resp.status_code == 200:
                img = QImage()
                img.loadFromData(resp.content)
                pm = QPixmap.fromImage(img).scaled(
                    self.lbl_image.width(), self.lbl_image.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.lbl_image.setPixmap(pm)
        except Exception:
            pass

    def _append_ai_log(self, reasoning: str, action_code: int = 0):
        if not reasoning:
            return
        action_map = {0: "Giữ nguyên", 1: "Bật bơm", 2: "Bật quạt", 3: "Bơm+Quạt", 5: "Bật đèn"}
        action_text = action_map.get(action_code, f"Code {action_code}")
        time_str = datetime.now().strftime("%H:%M:%S")
        self.txt_ai_log.append(f"[{time_str}] [{action_text}] {reasoning}\n")

    def _apply_device_states(self, states: dict):
        self.pump_state = states.get("pump", False)
        self.fan_state = states.get("fan", False)
        self.light_state = states.get("light", False)
        self._update_device_ui()

    def _update_device_ui(self):
        off = "background-color: #A0AEC0; border: none;"
        on_p = "background-color: #3182CE; border: none;"
        on_f = "background-color: #D69E2E; border: none;"
        on_l = "background-color: #48BB78; border: none;"

        self.btn_pump.setText(f'BƠM NƯỚC: {"ĐANG BẬT" if self.pump_state else "TẮT"}')
        self.btn_pump.setStyleSheet(on_p if self.pump_state else off)

        self.btn_fan.setText(f'QUẠT GIÓ: {"ĐANG BẬT" if self.fan_state else "TẮT"}')
        self.btn_fan.setStyleSheet(on_f if self.fan_state else off)

        self.btn_light.setText(f'ĐÈN: {"ĐANG BẬT" if self.light_state else "TẮT"}')
        self.btn_light.setStyleSheet(on_l if self.light_state else off)

        is_manual = not self.is_auto_mode
        self.btn_pump.setEnabled(is_manual)
        self.btn_fan.setEnabled(is_manual)
        self.btn_light.setEnabled(is_manual)

    # ── Mode toggle ─────────────────────────────────
    def _on_mode_toggle(self):
        self.is_auto_mode = self.rb_auto.isChecked()
        mode = "auto" if self.is_auto_mode else "manual"
        self.ws_thread.send({
            "type": "set_mode",
            "api_key": API_KEY,
            "node_id": self.current_node_id,
            "mode": mode,
        })
        self._update_device_ui()

        if self.is_auto_mode:
            self.txt_ai_log.append("[SYSTEM] Chuyển sang chế độ TỰ ĐỘNG.\n")
        else:
            self.txt_ai_log.append("[SYSTEM] Chuyển sang chế độ THỦ CÔNG.\n")

    # ── Device toggle (manual) ──────────────────────
    def _toggle_device(self, device: str):
        if self.is_auto_mode:
            self.txt_ai_log.append("[CẢNH BÁO] Không thể thao tác trong chế độ Tự động!\n")
            return

        current = {"pump": self.pump_state, "fan": self.fan_state, "light": self.light_state}
        is_on = current.get(device, False)

        if is_on:
            action_type = 0
        else:
            action_type = {"pump": 1, "fan": 2, "light": 5}[device]

        self.ws_thread.send({
            "type": "manual_action",
            "api_key": API_KEY,
            "node_id": self.current_node_id,
            "action_type": action_type,
        })

    # ── Cleanup ─────────────────────────────────────
    def closeEvent(self, event):
        self.ws_thread.stop()
        self.ws_thread.wait(2000)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartGardenDashboard()
    window.show()
    sys.exit(app.exec_())
