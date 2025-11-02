from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import psutil
import os

class TrayManager(QWidget):
    def __init__(self, tray_btn):
        super().__init__()
        self.tray_btn = tray_btn
        self.setWindowFlags(Qt.Popup)
        self.setStyleSheet("background-color: #222; color: white; border-radius: 10px;")
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(12, 12, 12, 12)
        self.layout().setSpacing(10)

    def show_popup(self):
        if self.isVisible():
            self.hide()
            return

        self.refresh_icons()
        pos = self.tray_btn.mapToGlobal(self.tray_btn.rect().bottomLeft())
        self.move(pos.x(), pos.y() + 8)
        self.adjustSize()
        self.show()

    def refresh_icons(self):
        tray_apps = {
            "discord.exe": "images/discord.png",
            "steam.exe": "images/tray/steam_tray_icon.png",
            "OneDrive.exe": "images/onedrive.png",
            "Telegram.exe": "images/telegram.png"
        }

        running = [p.name() for p in psutil.process_iter()]
        active_tray = [(name, icon) for name, icon in tray_apps.items() if name in running]

        while self.layout().count():
            item = self.layout().takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        if not active_tray:
            label = QLabel("Нет активных значков")
            label.setStyleSheet("font-size: 16px; color: #aaa;")
            self.layout().addWidget(label)
        else:
            for proc_name, icon_path in active_tray:
                row = QHBoxLayout()
                icon = QLabel()
                if os.path.exists(icon_path):
                    pix = QPixmap(icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    icon.setPixmap(pix)
                label = QLabel(proc_name.replace(".exe", ""))
                label.setStyleSheet("font-size: 16px; padding-left: 6px;")
                row.addWidget(icon)
                row.addWidget(label)
                row.addStretch()
                container = QWidget()
                container.setLayout(row)
                self.layout().addWidget(container)