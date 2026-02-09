import sys
import subprocess
import os
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, 
                             QDateEdit, QPushButton, QMessageBox, QLineEdit,
                             QHBoxLayout, QCheckBox, QFileDialog)
from PyQt6.QtCore import QDate, Qt, QEvent
from PyQt6.QtGui import QMouseEvent

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

class ClickableDateEdit(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        # Install event filter on the internal line edit to capture clicks
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                super().eventFilter(source, event)
                from PyQt6.QtGui import QKeyEvent
                new_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
                # app = QApplication.instance()
                # app.postEvent(self, new_event)
                pass 
            
        return super().eventFilter(source, event)

class LauncherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Korail Automation Launcher")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Start Date Row
        h_layout_start = QHBoxLayout()
        self.chk_start = QCheckBox("출발일")
        self.chk_start.setChecked(True)
        self.chk_start.stateChanged.connect(lambda state: self.start_date_edit.setEnabled(state == Qt.CheckState.Checked.value))
        h_layout_start.addWidget(self.chk_start)

        self.start_date_edit = AutoPopupDateEdit()
        # Restrict to last 3 months
        three_months_ago = QDate.currentDate().addMonths(-3)
        self.start_date_edit.setMinimumDate(three_months_ago)
        self.start_date_edit.setDate(QDate.currentDate().addDays(-7))
        h_layout_start.addWidget(self.start_date_edit)
        layout.addLayout(h_layout_start)

        # End Date Row
        h_layout_end = QHBoxLayout()
        self.chk_end = QCheckBox("도착일")
        self.chk_end.setChecked(True)
        self.chk_end.stateChanged.connect(lambda state: self.end_date_edit.setEnabled(state == Qt.CheckState.Checked.value))
        h_layout_end.addWidget(self.chk_end)

        self.end_date_edit = AutoPopupDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        h_layout_end.addWidget(self.end_date_edit)
        layout.addLayout(h_layout_end)

        # Save Path Row
        h_layout_path = QHBoxLayout()
        self.lbl_path = QLabel("저장 경로:")
        h_layout_path.addWidget(self.lbl_path)
        
        self.save_path_edit = QLineEdit()
        default_path = os.path.join(os.path.expanduser("~"), "Desktop", "출장복명")
        self.save_path_edit.setText(default_path)
        self.save_path_edit.setReadOnly(True)
        h_layout_path.addWidget(self.save_path_edit)

        self.btn_browse = QPushButton("폴더 선택")
        self.btn_browse.clicked.connect(self.browse_folder)
        h_layout_path.addWidget(self.btn_browse)

        layout.addLayout(h_layout_path)
        
        # Load settings if exists
        self.load_settings()
        
        # Ensure directory exists on launch
        if not os.path.exists(self.save_path_edit.text()):
            try:
                os.makedirs(self.save_path_edit.text())
            except:
                pass

        # Launch Button
        self.btn_launch = QPushButton("KTX 영수증 발급")
        self.btn_launch.clicked.connect(self.launch_automation)
        layout.addWidget(self.btn_launch)

        self.setLayout(layout)
        self.resize(300, 200)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if folder:
            self.save_path_edit.setText(folder)
            self.save_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'save_path' in data:
                        self.save_path_edit.setText(data['save_path'])
            except:
                pass

    def save_settings(self):
        try:
            data = {'save_path': self.save_path_edit.text()}
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            pass

    def launch_automation(self):
        # If checked, use date. If not, use wide range.
        if self.chk_start.isChecked():
            start_date = self.start_date_edit.date().toString("yyyyMMdd")
        else:
            start_date = "19000101" # Very old date
            
        if self.chk_end.isChecked():
            end_date = self.end_date_edit.date().toString("yyyyMMdd")
        else:
            end_date = "29991231" # Very future date

        # Command to run the korail_webview.py script
        script_path = os.path.join(os.path.dirname(__file__), "korail_webview.py")
        
        # Save settings before launch to ensure latest path is used
        self.save_settings()
        
        # Use simple python command
        cmd = [
            sys.executable, script_path, 
            "--start_date", start_date, 
            "--end_date", end_date,
            "--save_path", self.save_path_edit.text()
        ]

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch script: {e}")

class AutoPopupDateEdit(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.lineEdit().installEventFilter(self)

    def eventFilter(self, source, event):
        if source == self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.setFocus()
                from PyQt6.QtGui import QKeyEvent
                key_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
                QApplication.postEvent(self, key_event)
                
        return super().eventFilter(source, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LauncherApp()
    window.show()
    sys.exit(app.exec())
