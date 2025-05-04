from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QRect, QPropertyAnimation, QEasingCurve
import sqlite3
import os

class AnimatedButton(QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                border: none;
                border-radius: 12px;
            }
        """)

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(150)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)
        self.original_geometry = None

    def enterEvent(self, event):
        if not self.original_geometry:
            self.original_geometry = self.geometry()
        self.animate_scale(1.1)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animate_scale(1.0)
        super().leaveEvent(event)

    def animate_scale(self, scale):
        if not self.original_geometry:
            return
        rect = self.original_geometry
        new_width = int(rect.width() * scale)
        new_height = int(rect.height() * scale)
        x = rect.center().x() - new_width // 2
        y = rect.center().y() - new_height // 2
        new_rect = QRect(x, y, new_width, new_height)
        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(new_rect)
        self.anim.start()


def create_animated_button(icon_path, size, on_click=None, parent=None):
    btn = AnimatedButton(parent)
    btn.setIcon(QIcon(icon_path))
    btn.setIconSize(QSize(size, size))
    btn.setFixedSize(size, size)
    btn.setStyleSheet("border: none;")
    if on_click:
        btn.clicked.connect(on_click)
    return btn


def load_apps_from_db():
    db_path = "apps.db"
    if not os.path.exists(db_path):
        return [], []
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, path, type FROM apps")
    rows = cursor.fetchall()
    conn.close()
    games = [(name, path) for name, path, type_ in rows if type_ == "game"]
    apps = [(name, path) for name, path, type_ in rows if type_ == "app"]
    return games, apps
