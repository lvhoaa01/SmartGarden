import sys
import random
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QProgressBar, QTextEdit, QFrame, 
                             QGridLayout, QPushButton, QRadioButton, QButtonGroup, QSizePolicy)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor

class SmartHouseDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartHouse - Intelligent Control Panel")
        self.setGeometry(50, 50, 1366, 768)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F7FA;
            }
            QLabel {
                color: #2D3748;
                font-family: 'Segoe UI', Arial;
            }
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
            QProgressBar {
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                text-align: center;
                color: #2D3748;
                font-weight: bold;
                background-color: #EDF2F7;
            }
            QProgressBar::chunk {
                background-color: #48BB78;
                border-radius: 5px;
            }
            QTextEdit {
                background-color: #F8FAFC;
                color: #4A5568;
                font-family: 'Segoe UI', Arial;
                font-size: 15px;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton {
                font-family: 'Segoe UI', Arial;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
                padding: 10px;
                color: white;
            }
            QRadioButton {
                font-family: 'Segoe UI', Arial;
                font-size: 16px;
                font-weight: bold;
                color: #2D3748;
            }
            QRadioButton::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        
        self.countdown_seconds = 120
        self.is_auto_mode = True
        
        self.pump_state = False
        self.fan_state = False
        self.light_state = False
        
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(80)
        self.top_bar.setStyleSheet("background-color: #FFFFFF; border: none; border-bottom: 2px solid #E2E8F0; border-radius: 0px;")
        self.top_layout = QHBoxLayout(self.top_bar)
        
        lbl_app_name = QLabel("SmartHouse")
        lbl_app_name.setFont(QFont("Segoe UI", 24, QFont.Bold))
        lbl_app_name.setStyleSheet("color: #3182CE; border: none;")
        self.top_layout.addWidget(lbl_app_name)
        
        self.top_layout.addStretch()
        
        self.mode_group = QButtonGroup(self)
        self.rb_auto = QRadioButton("CHẾ ĐỘ TỰ ĐỘNG")
        self.rb_manual = QRadioButton("CHẾ ĐỘ THỦ CÔNG")
        self.rb_auto.setChecked(True)
        self.rb_auto.setStyleSheet("border: none;")
        self.rb_manual.setStyleSheet("border: none;")
        
        self.mode_group.addButton(self.rb_auto)
        self.mode_group.addButton(self.rb_manual)
        self.top_layout.addWidget(self.rb_auto)
        self.top_layout.addWidget(self.rb_manual)
        
        self.rb_auto.toggled.connect(self.toggle_mode)
        
        self.main_layout.addWidget(self.top_bar)
        
        self.content_layout = QHBoxLayout()
        self.main_layout.addLayout(self.content_layout)
        
        self.col_left = QVBoxLayout()
        self.col_mid = QVBoxLayout()
        self.col_right = QVBoxLayout()
        
        self.content_layout.addLayout(self.col_left, 3)
        self.content_layout.addLayout(self.col_mid, 3)
        self.content_layout.addLayout(self.col_right, 4)
        
        title_font = QFont("Segoe UI", 13, QFont.Bold)
        value_font = QFont("Segoe UI", 28, QFont.Bold)
        
        self.camera_frame = QFrame()
        self.camera_layout = QVBoxLayout(self.camera_frame)
        self.col_left.addWidget(self.camera_frame, 4)
        
        lbl_camera_title = QLabel("CAMERA GIÁM SÁT")
        lbl_camera_title.setFont(title_font)
        lbl_camera_title.setStyleSheet("color: #718096; border: none;")
        self.camera_layout.addWidget(lbl_camera_title)
        
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignCenter)
        self.lbl_image.setStyleSheet("border: 2px dashed #CBD5E0; background-color: #F7FAFC; border-radius: 8px;")
        self.camera_layout.addWidget(self.lbl_image)
        
        self.btn_manual_capture = QPushButton("📸 CHỤP MỚI & PHÂN TÍCH")
        self.btn_manual_capture.setStyleSheet("background-color: #3182CE; border: none;")
        self.btn_manual_capture.setFixedHeight(50)
        self.btn_manual_capture.clicked.connect(self.manual_trigger)
        self.btn_manual_capture.setVisible(False)
        self.camera_layout.addWidget(self.btn_manual_capture)
        
        self.timer_frame = QFrame()
        self.timer_layout = QVBoxLayout(self.timer_frame)
        self.col_left.addWidget(self.timer_frame, 1)
        
        self.lbl_timer_title = QLabel("THỜI GIAN LẤY MẪU TIẾP THEO")
        self.lbl_timer_title.setFont(title_font)
        self.lbl_timer_title.setStyleSheet("color: #718096; border: none;")
        self.lbl_timer_title.setAlignment(Qt.AlignCenter)
        self.timer_layout.addWidget(self.lbl_timer_title)
        
        self.lbl_countdown = QLabel("02:00")
        self.lbl_countdown.setFont(QFont("Segoe UI", 36, QFont.Bold))
        self.lbl_countdown.setStyleSheet("color: #E53E3E; border: none;")
        self.lbl_countdown.setAlignment(Qt.AlignCenter)
        self.timer_layout.addWidget(self.lbl_countdown)
        
        self.sensor_frame = QFrame()
        self.sensor_layout = QGridLayout(self.sensor_frame)
        self.sensor_layout.setSpacing(20)
        self.col_mid.addWidget(self.sensor_frame)
        
        lbl_sensor_title = QLabel("THÔNG SỐ MÔI TRƯỜNG")
        lbl_sensor_title.setFont(title_font)
        lbl_sensor_title.setStyleSheet("color: #718096; border: none;")
        lbl_sensor_title.setAlignment(Qt.AlignCenter)
        self.sensor_layout.addWidget(lbl_sensor_title, 0, 0, 1, 2)
        
        self.lbl_temp = QLabel("-- °C")
        self.lbl_temp.setFont(value_font)
        self.lbl_temp.setStyleSheet("border: none; color: #E53E3E;")
        lbl_t = QLabel("Nhiệt độ:")
        lbl_t.setStyleSheet("border: none; font-size: 16px; color: #4A5568;")
        self.sensor_layout.addWidget(lbl_t, 1, 0)
        self.sensor_layout.addWidget(self.lbl_temp, 1, 1)
        
        self.lbl_hum = QLabel("-- %")
        self.lbl_hum.setFont(value_font)
        self.lbl_hum.setStyleSheet("border: none; color: #3182CE;")
        lbl_h = QLabel("Độ ẩm KK:")
        lbl_h.setStyleSheet("border: none; font-size: 16px; color: #4A5568;")
        self.sensor_layout.addWidget(lbl_h, 2, 0)
        self.sensor_layout.addWidget(self.lbl_hum, 2, 1)
        
        self.pb_soil = QProgressBar()
        self.pb_soil.setRange(0, 100)
        self.pb_soil.setValue(0)
        self.pb_soil.setFixedHeight(30)
        lbl_s = QLabel("Độ ẩm Đất:")
        lbl_s.setStyleSheet("border: none; font-size: 16px; color: #4A5568;")
        self.sensor_layout.addWidget(lbl_s, 3, 0)
        self.sensor_layout.addWidget(self.pb_soil, 3, 1)
        
        self.lbl_light = QLabel("-- Lux")
        self.lbl_light.setFont(value_font)
        self.lbl_light.setStyleSheet("border: none; color: #D69E2E;")
        lbl_l = QLabel("Ánh sáng:")
        lbl_l.setStyleSheet("border: none; font-size: 16px; color: #4A5568;")
        self.sensor_layout.addWidget(lbl_l, 4, 0)
        self.sensor_layout.addWidget(self.lbl_light, 4, 1)

        self.ai_frame = QFrame()
        self.ai_layout = QVBoxLayout(self.ai_frame)
        self.col_right.addWidget(self.ai_frame, 3)
        
        lbl_ai_title = QLabel("AI QWEN VLM - SUY LUẬN LOGIC")
        lbl_ai_title.setFont(title_font)
        lbl_ai_title.setStyleSheet("color: #718096; border: none;")
        self.ai_layout.addWidget(lbl_ai_title)
        
        self.txt_ai_log = QTextEdit()
        self.txt_ai_log.setReadOnly(True)
        self.ai_layout.addWidget(self.txt_ai_log)
        
        self.action_frame = QFrame()
        self.action_layout = QVBoxLayout(self.action_frame)
        self.col_right.addWidget(self.action_frame, 2)
        
        lbl_action_title = QLabel("BẢNG ĐIỀU KHIỂN THIẾT BỊ")
        lbl_action_title.setFont(title_font)
        lbl_action_title.setStyleSheet("color: #718096; border: none;")
        lbl_action_title.setAlignment(Qt.AlignCenter)
        self.action_layout.addWidget(lbl_action_title)
        
        self.btn_pump = QPushButton("BƠM NƯỚC: TẮT")
        self.btn_fan = QPushButton("QUẠT GIÓ: TẮT")
        self.btn_light = QPushButton("ĐÈN QUANG HỢP: TẮT")
        
        self.btn_pump.setFixedHeight(45)
        self.btn_fan.setFixedHeight(45)
        self.btn_light.setFixedHeight(45)
        
        self.btn_pump.clicked.connect(lambda: self.toggle_device("pump"))
        self.btn_fan.clicked.connect(lambda: self.toggle_device("fan"))
        self.btn_light.clicked.connect(lambda: self.toggle_device("light"))
        
        self.action_layout.addWidget(self.btn_pump)
        self.action_layout.addWidget(self.btn_fan)
        self.action_layout.addWidget(self.btn_light)

        self.update_device_ui()
        self.refresh_data(triggered_by_ai=True)

        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

    def toggle_mode(self):
        self.is_auto_mode = self.rb_auto.isChecked()
        if self.is_auto_mode:
            self.lbl_timer_title.setText("THỜI GIAN LẤY MẪU TIẾP THEO")
            self.lbl_countdown.setStyleSheet("color: #E53E3E; border: none;")
            self.btn_manual_capture.setVisible(False)
            self.txt_ai_log.append("\n[SYSTEM] Đã chuyển sang chế độ TỰ ĐỘNG. AI giành quyền kiểm soát.\n")
        else:
            self.lbl_timer_title.setText("TRẠNG THÁI")
            self.lbl_countdown.setText("THỦ CÔNG")
            self.lbl_countdown.setStyleSheet("color: #718096; border: none;")
            self.btn_manual_capture.setVisible(True)
            self.txt_ai_log.append("\n[SYSTEM] Đã chuyển sang chế độ THỦ CÔNG. Bạn có toàn quyền điều khiển.\n")

    def update_clock(self):
        if not self.is_auto_mode:
            return
            
        self.countdown_seconds -= 1
        if self.countdown_seconds <= 0:
            self.countdown_seconds = 120
            self.refresh_data(triggered_by_ai=True)
            
        mins, secs = divmod(self.countdown_seconds, 60)
        self.lbl_countdown.setText(f"{mins:02d}:{secs:02d}")

    def manual_trigger(self):
        self.txt_ai_log.append(f"\n[{datetime.now().strftime('%H:%M:%S')}] Yêu cầu chụp ảnh thủ công...")
        self.refresh_data(triggered_by_ai=False)

    def toggle_device(self, device_name):
        if self.is_auto_mode:
            self.txt_ai_log.append("[CẢNH BÁO] Không thể thao tác tay trong chế độ Tự động!")
            return
            
        if device_name == "pump":
            self.pump_state = not self.pump_state
        elif device_name == "fan":
            self.fan_state = not self.fan_state
        elif device_name == "light":
            self.light_state = not self.light_state
            
        self.update_device_ui()

    def update_device_ui(self):
        btn_style_off = "background-color: #A0AEC0; border: none; color: white;"
        btn_style_on_pump = "background-color: #3182CE; border: none; color: white;"
        btn_style_on_fan = "background-color: #D69E2E; border: none; color: white;"
        btn_style_on_light = "background-color: #48BB78; border: none; color: white;"

        if self.pump_state:
            self.btn_pump.setText("BƠM NƯỚC: ĐANG BẬT")
            self.btn_pump.setStyleSheet(btn_style_on_pump)
        else:
            self.btn_pump.setText("BƠM NƯỚC: TẮT")
            self.btn_pump.setStyleSheet(btn_style_off)

        if self.fan_state:
            self.btn_fan.setText("QUẠT GIÓ: ĐANG BẬT")
            self.btn_fan.setStyleSheet(btn_style_on_fan)
        else:
            self.btn_fan.setText("QUẠT GIÓ: TẮT")
            self.btn_fan.setStyleSheet(btn_style_off)

        if self.light_state:
            self.btn_light.setText("ĐÈN QUANG HỢP: ĐANG BẬT")
            self.btn_light.setStyleSheet(btn_style_on_light)
        else:
            self.btn_light.setText("ĐÈN QUANG HỢP: TẮT")
            self.btn_light.setStyleSheet(btn_style_off)

    def update_mock_image(self):
        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor("#E2E8F0"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#4A5568"))
        font = QFont("Segoe UI", 14, QFont.Bold)
        painter.setFont(font)
        
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = f"📷 LIVE CAMERA FEED\n\nCaptured at:\n{time_str}\n\nStatus: OK"
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
        painter.end()
        
        self.lbl_image.setPixmap(pixmap)

    def refresh_data(self, triggered_by_ai=True):
        self.update_mock_image()
        
        t = round(random.uniform(28.0, 36.0), 1)
        h = round(random.uniform(40.0, 85.0), 1)
        s = int(random.uniform(20, 80))
        l = int(random.uniform(500, 4000))
        
        self.lbl_temp.setText(f"{t} °C")
        self.lbl_hum.setText(f"{h} %")
        self.pb_soil.setValue(s)
        self.lbl_light.setText(f"{l} Lux")
        
        ai_scenarios = [
            ("Môi trường đang ở trạng thái lý tưởng. Không phát hiện bất thường trên bề mặt lá.", 0),
            ("Hình ảnh cho thấy lá hơi rũ xuống. Thông số cho thấy đất đang rất khô (dưới 30%). Đề xuất bật bơm nước.", 1),
            ("Nhiệt độ hiện tại khá cao (trên 34 độ). Bề mặt lá có dấu hiệu sốc nhiệt. Đề xuất bật quạt làm mát.", 2),
            ("Cường độ ánh sáng quá thấp so với tiêu chuẩn. Đề xuất bật đèn quang hợp bù sáng.", 5),
            ("Cảnh báo: Phát hiện đốm bất thường trên lá. Đồng thời cần bật bơm và quạt để luân chuyển không khí.", 3)
        ]
        
        chosen_scenario = random.choice(ai_scenarios)
        
        if s < 35:
            chosen_scenario = ai_scenarios[1]
        elif t > 34.0:
            chosen_scenario = ai_scenarios[2]
        elif l < 1000:
            chosen_scenario = ai_scenarios[3]
            
        ai_text = chosen_scenario[0]
        action_code = chosen_scenario[1]
        
        time_str = datetime.now().strftime("%H:%M:%S")
        
        if triggered_by_ai:
            log_entry = f"[{time_str}] VLM Phân tích:\n> {ai_text}\n"
            self.txt_ai_log.append(log_entry)
            
            self.pump_state = False
            self.fan_state = False
            self.light_state = False
            
            if action_code in [1, 3]:
                self.pump_state = True
            if action_code in [2, 3]:
                self.fan_state = True
            if action_code == 5:
                self.light_state = True
                
            self.update_device_ui()
        else:
            log_entry = f"[{time_str}] AI Gợi ý:\n> {ai_text}\n(Chế độ thủ công: Lời khuyên không được tự động thực thi)\n"
            self.txt_ai_log.append(log_entry)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SmartHouseDashboard()
    window.show()
    sys.exit(app.exec_())