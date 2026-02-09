import sys
import threading
import datetime
import json
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QDateEdit, QPushButton, QTextEdit, QMessageBox, QFileDialog)
from PyQt6.QtCore import QDate, pyqtSignal, QObject
from srt_manager import SRTManager
from config import Config

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

class WorkerSignals(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

class SRTLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.manager = None

    def initUI(self):
        self.setWindowTitle('SRT 영수증 자동화')
        self.setGeometry(300, 300, 500, 300)

        layout = QVBoxLayout()

        # 1. Login Section - REMOVED for Manual Login
        # login_label = QLabel("SRT 로그인 정보")
        # layout.addWidget(login_label)

        # self.id_input = QLineEdit() ...
        
        info_label = QLabel("브라우저가 열리면 직접 로그인해주세요.")
        info_label.setStyleSheet("color: blue; font-weight: bold;")
        layout.addWidget(info_label)

        # 2. Date Section
        date_label = QLabel("조회 기간 설정")
        layout.addWidget(date_label)

        date_layout = QHBoxLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        # Default: 1 week ago
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        # Default: Today
        self.end_date.setDate(QDate.currentDate())
        
        date_layout.addWidget(QLabel("시작일:"))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel("종료일:"))
        date_layout.addWidget(self.end_date)
        
        layout.addLayout(date_layout)

        # 3. Path Selection Section
        path_label = QLabel("저장 경로")
        layout.addWidget(path_label)
        
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        
        # Default Path: Desktop/출장복명
        default_path = os.path.join(os.path.expanduser("~"), "Desktop", "출장복명")
        self.path_input.setText(default_path)
        
        self.browse_btn = QPushButton("폴더 선택")
        self.browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_btn)
        layout.addLayout(path_layout)
        
        # Load settings if exists
        self.load_settings()

        # 4. Action Section
        self.start_btn = QPushButton("브라우저 열기 및 영수증 출력")
        self.start_btn.clicked.connect(self.start_automation)
        self.start_btn.setFixedHeight(40)
        layout.addWidget(self.start_btn)
    
        # Spacer to push everything up
        layout.addStretch()

        self.setLayout(layout)
        
        # Signals
        self.signals = WorkerSignals()
        self.signals.finished_signal.connect(self.on_finished)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if folder:
            self.path_input.setText(folder)
            self.save_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'save_path' in data:
                        self.path_input.setText(data['save_path'])
            except:
                pass

    def save_settings(self):
        try:
            data = {'save_path': self.path_input.text()}
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            pass

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("브라우저 열기 및 영수증 출력")
        QMessageBox.information(self, "완료", "작업이 종료되었습니다.")

    def start_automation(self):
        start_date = self.start_date.date().toString("yyyyMMdd")
        end_date = self.end_date.date().toString("yyyyMMdd")
        save_path = self.path_input.text()
        
        if not os.path.exists(save_path):
            try:
                os.makedirs(save_path)
            except Exception as e:
                QMessageBox.warning(self, "오류", f"폴더 생성 실패: {e}")
                return

        self.start_btn.setEnabled(False)
        self.start_btn.setText("로그인 대기 중...")
        
        # Run in thread
        t = threading.Thread(target=self.run_logic, args=(start_date, end_date, save_path))
        t.daemon = True
        t.start()

    def run_logic(self, start_date, end_date, save_path):
        self.manager = SRTManager(headless=False, log_callback=self.signals.log_signal.emit)
        
        try:
            # Login (Manual)
            if self.manager.wait_for_login():
                self.signals.log_signal.emit("로그인 확인됨. 영수증 수집을 시작합니다.")
                
                self.manager.goto_receipt_page()
                
                # Pass dates and capture with checkbox logic
                self.manager.capture_with_checkbox(limit=100, start_date=start_date, end_date=end_date, save_dir=save_path)
            else:
                self.signals.log_signal.emit("로그인 실패 또는 중단됨.")
        except Exception as e:
            self.signals.log_signal.emit(f"오류 발생: {e}")
        finally:
            self.manager.close()
            self.signals.finished_signal.emit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SRTLauncher()
    ex.show()
    sys.exit(app.exec())
