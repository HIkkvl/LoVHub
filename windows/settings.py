import sqlite3
import psutil
import getpass
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEvent, QSize
from PyQt5.QtGui import QIcon
from utils.helpers import AnimatedButton
from PyQt5.QtCore import QTimer
from datetime import timedelta
from windows.main_window import restart_application
import os
import sys
import subprocess



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
        self.username = username
        self.time_left_seconds = self.get_time_left_from_db(username)
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

        self.time_label = QLabel(self.seconds_to_time_str(self.time_left_seconds))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 35px;")

        time_layout = QVBoxLayout()
        time_layout.addWidget(self.time_label)
        time_left_box.setLayout(time_layout)
        layout.addWidget(time_left_box, alignment=Qt.AlignHCenter)
        layout.addSpacing(20)

        self.balance = self.get_balance_from_db(username)

        balance_box = QWidget()
        balance_box.setFixedSize(411, 45)
        balance_box.setStyleSheet("""
            background-color: #333;
            border: none;
            border-radius: 0px;
        """)

        self.balance_label = QLabel(f"{self.balance} ₽")
        self.balance_label.setAlignment(Qt.AlignCenter)
        self.balance_label.setStyleSheet("font-size: 30px; color: #00FF00;")

        balance_layout = QVBoxLayout()
        balance_layout.addWidget(self.balance_label)
        balance_box.setLayout(balance_layout)

        layout.addWidget(balance_box, alignment=Qt.AlignHCenter)
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

        self.username = self.get_logged_in_username()
        self.time_left_seconds = self.get_time_left_from_db(self.username) or 0 

        if self.username:
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_timer)
            self.timer.start(1000)  # обновление каждую секунду

            # Таймер для синхронизации с БД
            self.sync_timer = QTimer()
            self.sync_timer.timeout.connect(self.sync_with_database)
            self.sync_timer.start(3000)

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_with_database)
        self.sync_timer.start(3000)



    def sync_with_database(self):
        # Обновляем время
        new_time = self.get_time_left_from_db(self.username)
        if new_time is not None and new_time != self.time_left_seconds:
            self.time_left_seconds = new_time
            self.time_label.setText(self.seconds_to_time_str(self.time_left_seconds))

            # Если время добавлено, но таймер остановлен — перезапускаем
            if self.time_left_seconds > 0 and not self.timer.isActive():
                self.timer.start(1000)

        # Обновляем баланс
        new_balance = self.get_balance_from_db(self.username)
        if new_balance is not None and new_balance != self.balance:
            self.balance = new_balance
            self.balance_label.setText(f"{self.balance} ₽")



    
    def seconds_to_time_str(self, seconds):
        # Проверяем, чтобы seconds не было None
        if seconds is None:
            seconds = 0  # Если None, заменяем на 0
        return str(timedelta(seconds=max(0, seconds)))


    def get_time_left_from_db(self, username):
        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT time_left FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] is not None else 0
        except Exception as e:
            print("Ошибка при получении времени:", e)
            return 0

        
    def update_timer(self):
        if self.time_left_seconds > 0:
            self.time_left_seconds -= 1
            self.time_label.setText(self.seconds_to_time_str(self.time_left_seconds))
            self.update_time_left_in_db(self.username, self.time_left_seconds)
        else:
            self.time_label.setText("Время вышло")
            self.timer.stop()
            self.kill_disallowed_apps()
            self.restart_application()

    def update_time_left_in_db(self, username, seconds):
        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET time_left = ? WHERE username = ?", (seconds, username))
            conn.commit()
            conn.close()
        except Exception as e:
            print("DB write error:", e)


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

    def kill_disallowed_apps(self):
        # Список имён процессов, которые нужно закрыть (можно дополнить)
        targets = ["chrome.exe", "firefox.exe", "opera.exe", "steam.exe", "notepad.exe", "game.exe"]

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] in targets:
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

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

    def get_balance_from_db(self, username):
        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except Exception as e:
            print("Ошибка при получении баланса:", e)
            return 0

    def update_balance_in_db(self, username, new_balance):
        try:
            conn = sqlite3.connect("users.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, username))
            conn.commit()
            conn.close()
        except Exception as e:
            print("Ошибка при обновлении баланса:", e)

