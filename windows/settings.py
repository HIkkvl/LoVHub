import sqlite3
import psutil
import getpass
from PyQt5.QtWidgets import QDialog, QLineEdit
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEvent, QSize, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal 
from utils.helpers import AnimatedButton
from datetime import timedelta
import os
import subprocess


class SettingsWindow(QWidget):
    time_expired = pyqtSignal()  # Новый сигнал
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setObjectName("Settings")
        self.scale_factor = parent.scale_factor if parent else 1.0
        self.setFixedSize(int(450 * self.scale_factor), int(850 * self.scale_factor))
        self.setContentsMargins(14,0,0,0)
      #  self.setStyleSheet("background-color: #212121; color: white; border-radius: 10px;")

        layout = QVBoxLayout()

        # Секция приветствия
        hi_layout = QHBoxLayout()
        hi_label = QLabel("Hi!")
        hi_label.setStyleSheet("font-size: 44px; margin-left:114px; margin-top: 20px; background:none;")

        username = self.get_logged_in_username()
        self.username = username
        self.time_left_seconds = self.get_time_left_from_db(username)
        
        username_label = QLabel(username if username else "Guest")
        username_label.setStyleSheet("font-size: 44px; margin-left: 4px; margin-top: 20px; background:none;")

        hi_layout.addWidget(hi_label)
        hi_layout.addWidget(username_label)
        hi_layout.addStretch()
        layout.addLayout(hi_layout)

        # Секция информации о компьютере
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

        # Секция оставшегося времени
        time_left_box = QWidget()
        time_left_box.setObjectName("timer")
        time_left_box.setFixedSize(411, 45)

        self.time_label = QLabel(self.seconds_to_time_str(self.time_left_seconds))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 35px; background:none;")

        time_layout = QVBoxLayout()
        time_layout.addWidget(self.time_label)
        time_left_box.setLayout(time_layout)
        layout.addWidget(time_left_box, alignment=Qt.AlignHCenter)
        layout.addSpacing(20)


        # Секция пакетов времени
        packages_layout = QVBoxLayout()
        packages_layout.setSpacing(10)
        
        # Первый ряд кнопок (3 кнопки)
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)
        
        # Пакет 1: 30 минут за 350тг
        pkg1_btn = AnimatedButton("30 мин\n150 тг")
        pkg1_btn.setFixedSize(120, 80)
        pkg1_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        pkg1_btn.clicked.connect(lambda: self.buy_time_package(1800, 150))
        row1_layout.addWidget(pkg1_btn)
        
        # Пакет 2: 1 час за 350тг
        pkg2_btn = AnimatedButton("1 час\n350тг")
        pkg2_btn.setFixedSize(120, 80)
        pkg2_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        pkg2_btn.clicked.connect(lambda: self.buy_time_package(3600, 350))
        row1_layout.addWidget(pkg2_btn)
        
        # Пакет 3: 2 часа за 700 тг
        pkg3_btn = AnimatedButton("2 часа\n700 тг")
        pkg3_btn.setFixedSize(120, 80)
        pkg3_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        pkg3_btn.clicked.connect(lambda: self.buy_time_package(7200, 150))
        row1_layout.addWidget(pkg3_btn)
        
        packages_layout.addLayout(row1_layout)
        
        # Второй ряд кнопок (3 кнопки)
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)
        
        # Пакет 4: 3 часа за 1000 руб
        pkg4_btn = AnimatedButton("3 часа\n1000 тг")
        pkg4_btn.setFixedSize(120, 80)
        pkg4_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        pkg4_btn.clicked.connect(lambda: self.buy_time_package(10800, 200))
        row2_layout.addWidget(pkg4_btn)
        
        # Пакет 5: 5 часов за 2000 тг
        pkg5_btn = AnimatedButton("5 часов\n2000 тг")
        pkg5_btn.setFixedSize(120, 80)
        pkg5_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        pkg5_btn.clicked.connect(lambda: self.buy_time_package(18000, 2000))
        row2_layout.addWidget(pkg5_btn)
        
        # Пакет 6: 10 часов за 3500 тг
        pkg6_btn = AnimatedButton("10 часов\n3500 тг")
        pkg6_btn.setFixedSize(120, 80)
        pkg6_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)
        pkg6_btn.clicked.connect(lambda: self.buy_time_package(36000, 3500))
        row2_layout.addWidget(pkg6_btn)
        
        packages_layout.addLayout(row2_layout)
        layout.addLayout(packages_layout)
        layout.addSpacing(20)

        # Секция баланса и кнопки темы (новый layout)
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(23, 0, 0, 14)  # Отступы слева и снизу
        bottom_layout.setSpacing(6)  # Расстояние между элементами

        self.balance = self.get_balance_from_db(username)
        balance_box = QWidget()
        balance_box.setObjectName("balance_box")
        balance_box.setFixedSize(206, 50)

        balance_box.mousePressEvent = self.show_topup_dialog

        # Горизонтальный layout для иконки и текста баланса
        balance_layout = QHBoxLayout()
        balance_layout.setContentsMargins(8, 0, 30, 0)
        balance_layout.setSpacing(0)
        
        # Иконка баланса
        icon_label = QLabel()
        icon_label.setPixmap(QIcon("images/Balance_card.png").pixmap(48, 48))
        icon_label.setStyleSheet("background:none;")
        balance_layout.addWidget(icon_label)
        
        # Текст баланса
        self.balance_label = QLabel(f"{self.balance} тг")
        self.balance_label.setStyleSheet("font-size: 32px; color: #FFFFFF; background:none;")
        balance_layout.addWidget(self.balance_label)
        
        balance_box.setLayout(balance_layout)
        bottom_layout.addWidget(balance_box)

        # Кнопка смены темы
        self.theme_btn = AnimatedButton()
        self.theme_btn.setIcon(QIcon("images/dark_them_icon.png"))
        self.theme_btn.setIconSize(QSize(80, 80))
        self.theme_btn.setFixedSize(64, 64)
        self.theme_btn.setStyleSheet("background: none; border: none;")
        self.theme_btn.clicked.connect(self.change_theme)
        bottom_layout.addWidget(self.theme_btn)

        bottom_layout.addStretch()  # Растягиваемое пространство справа

        # Добавляем нижний layout в основной
        layout.addStretch()  # Растягиваемое пространство перед нижней панелью
        layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.is_closing = False
        self.installEventFilter(self)

        # Инициализация таймеров
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_with_database)
        
        # Автоматический запуск таймеров при наличии пользователя
        if username:
            self.start_timers()

    def show_topup_dialog(self, event):
        """Показывает диалоговое окно для пополнения баланса"""
        if not self.username:
            QMessageBox.warning(self, "Ошибка", "Необходимо войти в систему")
            return
            
        # Создаем диалоговое окно
        dialog = QDialog(self)
        dialog.setWindowTitle("Пополнение баланса")
        dialog.setFixedSize(300, 150)
        dialog.setStyleSheet("background-color: #212121; color: white;")
        
        layout = QVBoxLayout()
        
        # Поле для ввода суммы
        amount_label = QLabel("Введите сумму пополнения (тг):")
        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QIntValidator(1, 100000))  # Только целые числа от 1 до 100000
        self.amount_input.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                font-size: 16px;
            }
        """)
        
        # Кнопки подтверждения/отмены
        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("Пополнить")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        ok_btn.clicked.connect(lambda: self.topup_balance(dialog))
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addWidget(amount_label)
        layout.addWidget(self.amount_input)
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)

        center_point = QApplication.desktop().screen().rect().center()
        dialog_rect = dialog.frameGeometry()
        dialog_rect.moveCenter(center_point)
        dialog.move(dialog_rect.topLeft())
        
        dialog.exec_()

    def topup_balance(self, dialog):
        """Пополняет баланс на указанную сумму"""
        try:
            amount = int(self.amount_input.text())
            if amount <= 0:
                QMessageBox.warning(self, "Ошибка", "Сумма должна быть положительной")
                return
                
            self.balance += amount
            self.balance_label.setText(f"{self.balance} тг")
            self.update_balance_in_db(self.username, self.balance)
            QMessageBox.information(self, "Успешно", f"Баланс пополнен на {amount} тг")
            dialog.accept()
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму")

    def buy_time_package(self, seconds, price):
        """Покупка пакета времени"""
        if not self.username:
            QMessageBox.warning(self, "Ошибка", "Необходимо войти в систему")
            return
            
        if self.balance < price:
            QMessageBox.warning(self, "Ошибка", "Недостаточно средств на балансе")
            return
            
        # Обновляем баланс и время
        self.balance -= price
        self.time_left_seconds += seconds
        
        # Обновляем отображение
        self.balance_label.setText(f"{self.balance} ₽")
        self.time_label.setText(self.seconds_to_time_str(self.time_left_seconds))
        
        # Обновляем базу данных
        self.update_balance_in_db(self.username, self.balance)
        self.update_time_left_in_db(self.username, self.time_left_seconds)
        
        # Если таймер был остановлен (время закончилось), перезапускаем его
        if not self.timer.isActive() and self.time_left_seconds > 0:
            self.timer.start(1000)
            
        QMessageBox.information(self, "Успешно", f"Пакет времени приобретен! Добавлено {seconds//60} минут")

    def start_timers(self):
        """Запускает все необходимые таймеры"""
        if not self.timer.isActive():
            self.timer.start(1000)  # Обновление каждую секунду
        
        if not self.sync_timer.isActive():
            self.sync_timer.start(3000)  # Синхронизация с БД каждые 3 секунды

    # Остальные методы класса остаются без изменений
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
        if seconds is None:
            seconds = 0
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
            
            # Добавляем проверку на малое оставшееся время 
            if self.time_left_seconds == 300: 
                self.show_time_warning("Осталось 5 минут!")
        else:
            self.time_label.setText("Время вышло")
            self.timer.stop()
            self.kill_disallowed_apps()
            self.time_expired.emit()  # Отправляем сигнал о завершении времени

    def show_time_warning(self, message):
        if self.parent():
            QMessageBox.warning(self.parent(), "Внимание", message)

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