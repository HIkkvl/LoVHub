import sqlite3
import getpass
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEvent, QSize
from PyQt5.QtGui import QIcon
from utils.helpers import AnimatedButton


class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setFixedSize(450, 850)
        self.setStyleSheet("background-color: #212121; color: white; border-radius: 10px;")

        layout = QVBoxLayout()

        hi_layout = QHBoxLayout()
        hi_label = QLabel("Hi!")
        hi_label.setStyleSheet("font-size: 44px; margin-left:114px; margin-top: 20px;")

        username = self.get_logged_in_username()
        username_label = QLabel(username if username else "Guest")
        username_label.setStyleSheet("font-size: 44px; margin-left: 4px; margin-top: 20px;")

        hi_layout.addWidget(hi_label)
        hi_layout.addWidget(username_label)
        hi_layout.addStretch()
        layout.addLayout(hi_layout)


        windows_username = getpass.getuser()
        computer_box = QWidget()
        computer_box.setFixedSize(111, 111)
        computer_box.setStyleSheet("""
            background-color: #EAA21B;
            border: none;
            border-radius: 10px;
            margin-top: 34px;
        """)

        computer_label = QLabel(windows_username)
        computer_label.setAlignment(Qt.AlignCenter)
        computer_label.setStyleSheet("font-size: 20px;")

        box_layout = QVBoxLayout()
        box_layout.addWidget(computer_label)
        computer_box.setLayout(box_layout)

        layout.addWidget(computer_box, alignment=Qt.AlignHCenter)
        layout.addSpacing(20)

        time_left_box = QWidget()
        time_left_box.setFixedSize(411, 45)
        time_left_box.setStyleSheet("""
            background-color: #121212;
            border: none;
            border-radius: 0px;
        """)

        time_label = QLabel("23:59:00")
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setStyleSheet("font-size: 35px;")

        time_layout = QVBoxLayout()
        time_layout.addWidget(time_label)
        time_left_box.setLayout(time_layout)

        layout.addWidget(time_left_box, alignment=Qt.AlignHCenter)
        layout.addSpacing(20)

        self.theme_btn = AnimatedButton()
        self.theme_btn.setIcon(QIcon("images/dark_them_icon.png"))
        self.theme_btn.setIconSize(QSize(80, 80))
        self.theme_btn.setFixedSize(64, 64)
        self.theme_btn.setStyleSheet("background: none;")
        self.theme_btn.clicked.connect(self.change_theme)
        layout.addWidget(self.theme_btn)
        layout.addStretch()

        self.setLayout(layout)
        self.is_closing = False
        self.installEventFilter(self)

    def get_logged_in_username(self):
        try:
            with open("last_login.txt", "r") as f:
                username = f.read().strip()
                return username
        except FileNotFoundError:
            return None

    def show_with_animation(self, target_pos):
        start_x = target_pos.x() + self.width()
        self.move(start_x, target_pos.y())
        self.show()

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(300)
        self.anim.setStartValue(QRect(start_x, target_pos.y(), self.width(), self.height()))
        self.anim.setEndValue(QRect(target_pos.x(), target_pos.y(), self.width(), self.height()))
        self.anim.start()

    def close_with_animation(self):
        if self.is_closing:
            return
        self.is_closing = True

        screen_width = self.parent().width() if self.parent() else 1920
        end_x = screen_width

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(300)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(QRect(end_x, self.y(), self.width(), self.height()))

        def on_finished():
            self.close()
            self.is_closing = False
            if self.parent():
                self.parent().settings_open = False

        self.anim.finished.connect(on_finished)
        self.anim.start()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if not self.rect().contains(self.mapFromGlobal(event.globalPos())):
                self.close_with_animation()
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if not self.is_closing:
            event.ignore()
            self.close_with_animation()
        else:
            event.accept()

    def change_theme(self):
        if self.parent():
            self.parent().toggle_theme()
