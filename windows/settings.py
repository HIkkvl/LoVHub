import psutil
import getpass
import os
import json
import socket
import webbrowser 
from PyQt5.QtWidgets import (QGraphicsDropShadowEffect, QDialog, QLineEdit, 
                             QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QMessageBox, QPushButton)
from PyQt5.QtGui import QColor, QIntValidator, QIcon
from PyQt5.QtCore import Qt, QPropertyAnimation, QRect, QEvent, QSize, QTimer, pyqtSignal
from utils.helpers import AnimatedButton
from datetime import timedelta

from utils.workers import (StatusWorker, SyncTimeWorker, BuyPackageWorker, 
                           TopUpBalanceWorker, SyncLoopWorker) 


CACHE_DIR = "cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


class SettingsWindow(QWidget):
    time_expired = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent) 
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setObjectName("Settings")
        self.scale_factor = parent.scale_factor if parent else 1.0
        self.setFixedSize(int(450 * self.scale_factor), int(850 * self.scale_factor))
        
        self.container = QWidget(self)
        self.container.setObjectName("SettingsContainer")
        self.container.setGeometry(0, 0, self.width(), self.height())
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32); shadow.setXOffset(-15); shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(14, 0, 14, 14)

        hi_layout = QHBoxLayout()
        hi_label = QLabel("Hi!")
        hi_label.setStyleSheet("font-size: 44px; margin-left:114px; margin-top: 20px; background:none;")

        username = self.get_logged_in_username()
        self.username = username
        self.user_cache_file = os.path.join(CACHE_DIR, f"{self.username}.json") if self.username else ""
        self.pc_name = socket.gethostname() 

        self.time_left_seconds = 0 
        self.balance = 0
        self.workers = [] 
        
        self.load_from_cache() 
        
        username_label = QLabel(username if username else "Guest")
        username_label.setStyleSheet("font-size: 44px; margin-left: 4px; margin-top: 20px; background:none;")
        hi_layout.addWidget(hi_label); hi_layout.addWidget(username_label); hi_layout.addStretch()
        layout.addLayout(hi_layout)

        windows_username = getpass.getuser()
        computer_box = QWidget()
        computer_box.setFixedSize(111, 111)
        computer_box.setStyleSheet("background-color: #EAA21B; border: none; border-radius: 10px; margin-top: 34px;")
        computer_label = QLabel(windows_username)
        computer_label.setAlignment(Qt.AlignCenter)
        computer_label.setStyleSheet("font-size: 20px;")
        box_layout = QVBoxLayout()
        box_layout.addWidget(computer_label)
        computer_box.setLayout(box_layout)
        layout.addWidget(computer_box, alignment=Qt.AlignHCenter)
        layout.addSpacing(20)
        
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
        
        packages_layout = QVBoxLayout()
        packages_layout.setSpacing(10)
        row1_layout = QHBoxLayout(); row1_layout.setSpacing(10)
        self.pkg1_btn = AnimatedButton("30 мин\n150 тг")
        self.pkg1_btn.setFixedSize(120, 80); self.pkg1_btn.setStyleSheet("QPushButton { background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #EAA21B, stop:1 #473E2D); color: white; border-radius: 5px; font-size: 16px; }")
        self.pkg1_btn.clicked.connect(lambda: self.buy_time_package("30 мин", 1800, 150)); row1_layout.addWidget(self.pkg1_btn)
        self.pkg2_btn = AnimatedButton("1 час\n350тг")
        self.pkg2_btn.setFixedSize(120, 80); self.pkg2_btn.setStyleSheet("QPushButton { background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #EAA21B, stop:1 #473E2D); color: white; border-radius: 5px; font-size: 16px; }")
        self.pkg2_btn.clicked.connect(lambda: self.buy_time_package("1 час", 3600, 350)); row1_layout.addWidget(self.pkg2_btn)
        self.pkg3_btn = AnimatedButton("2 часа\n700 тг")
        self.pkg3_btn.setFixedSize(120, 80); self.pkg3_btn.setStyleSheet("QPushButton { background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #EAA21B, stop:1 #473E2D); color: white; border-radius: 5px; font-size: 16px; }")
        self.pkg3_btn.clicked.connect(lambda: self.buy_time_package("2 часа", 7200, 700)); row1_layout.addWidget(self.pkg3_btn)
        packages_layout.addLayout(row1_layout)
        row2_layout = QHBoxLayout(); row2_layout.setSpacing(10)
        self.pkg4_btn = AnimatedButton("3 часа\n1000 тг")
        self.pkg4_btn.setFixedSize(120, 80); self.pkg4_btn.setStyleSheet("QPushButton { background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #EAA21B, stop:1 #473E2D); color: white; border-radius: 5px; font-size: 16px; }")
        self.pkg4_btn.clicked.connect(lambda: self.buy_time_package("3 часа", 10800, 1000)); row2_layout.addWidget(self.pkg4_btn)
        self.pkg5_btn = AnimatedButton("5 часов\n2000 тг")
        self.pkg5_btn.setFixedSize(120, 80); self.pkg5_btn.setStyleSheet("QPushButton { background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #EAA21B, stop:1 #473E2D); color: white; border-radius: 5px; font-size: 16px; }")
        self.pkg5_btn.clicked.connect(lambda: self.buy_time_package("5 часов", 18000, 2000)); row2_layout.addWidget(self.pkg5_btn)
        self.pkg6_btn = AnimatedButton("10 часов\n3500 тг")
        self.pkg6_btn.setFixedSize(120, 80); self.pkg6_btn.setStyleSheet("QPushButton { background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #EAA21B, stop:1 #473E2D); color: white; border-radius: 5px; font-size: 16px; }")
        self.pkg6_btn.clicked.connect(lambda: self.buy_time_package("10 часов", 36000, 3500)); row2_layout.addWidget(self.pkg6_btn)
        self.all_pkg_buttons = [self.pkg1_btn, self.pkg2_btn, self.pkg3_btn, self.pkg4_btn, self.pkg5_btn, self.pkg6_btn]
        packages_layout.addLayout(row2_layout); layout.addLayout(packages_layout); layout.addSpacing(20)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(23, 0, 0, 14); bottom_layout.setSpacing(6)
        balance_box = QWidget(); balance_box.setObjectName("balance_box"); balance_box.setFixedSize(206, 50)
        balance_box.mousePressEvent = self.show_topup_dialog
        balance_layout = QHBoxLayout(); balance_layout.setContentsMargins(8, 0, 30, 0); balance_layout.setSpacing(0)
        icon_label = QLabel(); icon_label.setPixmap(QIcon("images/Balance_card.png").pixmap(48, 48)); icon_label.setStyleSheet("background:none;")
        balance_layout.addWidget(icon_label)
        self.balance_label = QLabel(f"{self.balance} тг"); self.balance_label.setStyleSheet("font-size: 32px; color: #FFFFFF; background:none;")
        balance_layout.addWidget(self.balance_label); balance_box.setLayout(balance_layout); bottom_layout.addWidget(balance_box)
        self.theme_btn = AnimatedButton(); self.theme_btn.setIcon(QIcon("images/dark_them_icon.png"))
        self.theme_btn.setIconSize(QSize(80, 80)); self.theme_btn.setFixedSize(64, 64)
        self.theme_btn.setStyleSheet("background: none; border: none;"); self.theme_btn.clicked.connect(self.change_theme)
        bottom_layout.addWidget(self.theme_btn); bottom_layout.addStretch(); layout.addStretch(); layout.addLayout(bottom_layout)

        self.setLayout(layout)
        self.is_closing = False
        self.installEventFilter(self)

        self.sync_loop_worker = None 
        
        if username:
            self.start_timers()
            self.update_status_from_server() 

    def load_from_cache(self):
        if not self.user_cache_file: return
        try:
            if os.path.exists(self.user_cache_file):
                with open(self.user_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.balance = data.get('balance', 0)
                    self.time_left_seconds = data.get('time_left', 0)
                print(f"Settings: Загружено из кэша: {self.balance} тг, {self.time_left_seconds} сек")
            else:
                print("Settings: Файл кэша не найден.")
        except Exception as e:
            print(f"Settings: Ошибка загрузки кэша: {e}")

    def save_to_cache(self, balance, time_left):
        if not self.user_cache_file: return
        try:
            with open(self.user_cache_file, 'w', encoding='utf-8') as f:
                json.dump({'balance': balance, 'time_left': time_left}, f)
        except Exception as e:
            print(f"Settings: Ошибка сохранения кэша: {e}")

    def show_topup_dialog(self, event):
        if not self.username:
            QMessageBox.warning(self, "Ошибка", "Необходимо войти в систему")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Пополнение баланса")
        dialog.setFixedSize(300, 150) 
        dialog.setStyleSheet("background-color: #212121; color: white;")
        
        layout = QVBoxLayout()
        
        amount_label = QLabel("Введите сумму пополнения (тг):")
        self.amount_input = QLineEdit()
        self.amount_input.setValidator(QIntValidator(1, 100000))
        self.amount_input.setStyleSheet("QLineEdit { background-color: #333; color: white; border: 1px solid #555; padding: 5px; font-size: 16px; }")
        
        buttons_layout = QHBoxLayout()
        ok_btn = QPushButton("К оплате") 
        ok_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border: none; padding: 8px; font-size: 14px; } QPushButton:hover { background-color: #45a049; }")
        
        ok_btn.clicked.connect(lambda: self.topup_balance(dialog))
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; border: none; padding: 8px; font-size: 14px; } QPushButton:hover { background-color: #d32f2f; }")
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addWidget(amount_label)
        layout.addWidget(self.amount_input)
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)

        center_point = QApplication.desktop().screen().rect().center()
        dialog_rect = dialog.frameGeometry(); dialog_rect.moveCenter(center_point)
        dialog.move(dialog_rect.topLeft()); dialog.exec_()

    def topup_balance(self, dialog):
        try:
            amount = int(self.amount_input.text())
            if amount <= 0:
                QMessageBox.warning(self, "Ошибка", "Сумма должна быть положительной"); return

            print(f"Settings: Создаем счет на {amount} тг для {self.username}...")
            dialog.accept() 

            worker = TopUpBalanceWorker(
                self.username, 
                amount
            )
            worker.finished.connect(self.on_payment_url_received) 
            worker.error.connect(self.on_top_up_error)
            
            self.workers.append(worker) 
            worker.finished.connect(lambda: self.workers.remove(worker) if worker in self.workers else None)
            worker.start()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму")

    def on_payment_url_received(self, payment_url):
        """ (НОВЫЙ СЛОТ) Сработал, когда воркер получил ссылку на оплату """
        print(f"Settings: Получена ссылка на оплату, открываем браузер: {payment_url}")
        
        QMessageBox.information(self, "Переход к оплате", 
            "Сейчас откроется ваш браузер для завершения оплаты.\n\n"
            "После успешной оплаты ваш баланс будет пополнен автоматически.")
        
        webbrowser.open(payment_url)
        
    def on_top_up_error(self, error_message):
        print(f"Settings: Ошибка создания счета: {error_message}")
        if "401" in error_message:
             QMessageBox.warning(self, "Ошибка", 
                "Не удалось создать счет. Ошибка авторизации сервера.")
        else:
            QMessageBox.warning(self, "Ошибка", f"Не удалось создать счет:\n{error_message}")

    def buy_time_package(self, package_name, seconds, price):
        if not self.username:
            QMessageBox.warning(self, "Ошибка", "Необходимо войти в систему"); return
        if self.balance < price:
            QMessageBox.warning(self, "Ошибка", "Недостаточно средств на балансе"); return
        self.set_package_buttons_enabled(False)
        worker = BuyPackageWorker(self.username, seconds, price, package_name, self.pc_name)
        worker.finished.connect(self.on_package_bought); worker.error.connect(self.on_package_buy_error)
        self.workers.append(worker)
        worker.finished.connect(lambda: self.workers.remove(worker) if worker in self.workers else None)
        worker.start()

    def on_package_bought(self, new_balance, new_time):
        print(f"Settings: Пакет куплен. Баланс: {new_balance}, Время: {new_time}")
        self.balance = new_balance
        self.balance_label.setText(f"{self.balance} тг")
        if self.parent():
            self.parent().start_core_timer(new_time)
        else:
            print("Settings: Ошибка, не найден self.parent() для перезапуска таймера!")
        QMessageBox.information(self, "Успешно", "Пакет времени приобретен!")
        self.set_package_buttons_enabled(True)
        self.save_to_cache(self.balance, new_time) 

    def on_package_buy_error(self, error_message):
        QMessageBox.warning(self, "Ошибка", f"Не удалось купить пакет:\n{error_message}")
        self.set_package_buttons_enabled(True)
        self.sync_with_database()

    def set_package_buttons_enabled(self, enabled):
        for btn in self.all_pkg_buttons:
            btn.setEnabled(enabled)
            btn.setStyleSheet(btn.styleSheet() + f" opacity: {1.0 if enabled else 0.5};")

    def start_timers(self):
        if not self.sync_loop_worker:
            self.sync_loop_worker = SyncLoopWorker(5) # (5 секунд)
            self.sync_loop_worker.trigger.connect(self.sync_with_database)
            
            self.workers.append(self.sync_loop_worker)
            self.sync_loop_worker.finished.connect(lambda: self.workers.remove(self.sync_loop_worker) if self.sync_loop_worker in self.workers else None)

            self.sync_loop_worker.start()
            print("Settings: Надежный SyncLoopWorker (5 сек) запущен.")
        
    def sync_with_database(self):
        self.update_status_from_server() 
        try:
            current_time = self.time_left_seconds 
            worker = SyncTimeWorker(self.username, current_time)
            worker.error.connect(lambda e: print(f"Settings: Ошибка фоновой синхронизации: {e}"))
            self.workers.append(worker)
            worker.finished.connect(lambda: self.workers.remove(worker) if worker in self.workers else None)
            worker.start()
        except Exception as e:
            print(f"Settings: Ошибка запуска SyncTimeWorker: {e}")

    def update_status_from_server(self):
        if not self.username: return
        worker = StatusWorker(self.username)
        worker.finished.connect(self.on_status_loaded)
        worker.error.connect(self.on_status_error)
        self.workers.append(worker)
        worker.finished.connect(lambda: self.workers.remove(worker) if worker in self.workers else None)
        worker.start()

    def on_status_loaded(self, balance, time_left):
        print(f"Settings: Синхронизация с сервером: Баланс={balance}, Время={time_left}")
        self.balance = balance
        self.balance_label.setText(f"{self.balance} тг")
        
        if not self.parent():
             print("Settings: Ошибка, не найден self.parent() для синхронизации таймера!")
             self.time_label.setText(self.seconds_to_time_str(time_left)) 
             return

        current_local_time = 0
        if self.parent().core_timer and self.parent().core_timer.isRunning():
            current_local_time = self.parent().core_timer.time_left
        
        if abs(current_local_time - time_left) > 5:
            print(f"Settings: Расхождение времени (Лок: {current_local_time} / Серв: {time_left}). Перезапуск таймера.")
            self.parent().start_core_timer(time_left)
        
        elif time_left > 0 and (not self.parent().core_timer or not self.parent().core_timer.isRunning()):
            print("Settings: Таймер не был активен, запускаем.")
            self.parent().start_core_timer(time_left)
            
        self.save_to_cache(self.balance, time_left)
    
    def on_status_error(self, error_message):
        print(f"Settings: Ошибка загрузки статуса (ОФФЛАЙН): {error_message}")
        
        if not self.parent():
             print("Settings: Ошибка, не найден self.parent() (оффлайн-старт)")
             return
             
        if self.time_left_seconds > 0 and (not self.parent().core_timer or not self.parent().core_timer.isRunning()):
            print(f"Settings: Сервер оффлайн, запускаем таймер из кэша ({self.time_left_seconds} сек)")
            self.parent().start_core_timer(self.time_left_seconds)

    def seconds_to_time_str(self, seconds):
        if seconds is None:
            seconds = 0
        return str(timedelta(seconds=max(0, seconds)))

    def show_time_warning(self, message):
        if self.parent():
            QMessageBox.warning(self.parent(), "Внимание", message)

    def get_logged_in_username(self):
        try:
            with open("last_login.txt", "r", encoding='utf-8') as f:
                username = f.read().strip()
                return username
        except FileNotFoundError:
            return None

    def show_with_animation(self, target_pos):
        parent_rect = self.parent().geometry() if self.parent() else QApplication.desktop().screen().rect()
        x_pos = parent_rect.right() - self.width()
        y_pos = target_pos.y()
        start_x = x_pos + self.width()
        self.move(start_x, y_pos)
        self.show()
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(300)
        self.anim.setStartValue(QRect(start_x, y_pos, self.width(), self.height()))
        self.anim.setEndValue(QRect(x_pos, y_pos, self.width(), self.height()))
        self.anim.start()

    def close_with_animation(self):
        self.save_to_cache(self.balance, self.time_left_seconds)
        if self.is_closing: return
        self.is_closing = True
        end_x = self.x() + self.width()
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
            if self.sync_loop_worker:
                self.sync_loop_worker.stop()
                self.sync_loop_worker.wait() 
                print("Settings: SyncLoopWorker остановлен.")
            event.accept()

    def change_theme(self):
        if self.parent():
            self.parent().toggle_theme()