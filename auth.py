import sys
import sqlite3
import subprocess
from PyQt5.QtWidgets import (QGraphicsBlurEffect, QGraphicsColorizeEffect, 
                            QMessageBox, QDialog)
from utils.helpers import AnimatedButton
from PyQt5.QtCore import (QPropertyAnimation, QEasingCurve, QSize, Qt, 
                         QRect, QEvent, QTimer, QTime, QDate)
from PyQt5.QtGui import (QIcon, QPixmap, QKeySequence, QPainter, 
                        QLinearGradient, QColor)
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                            QHBoxLayout, QInputDialog, QLineEdit, QScrollArea, 
                            QSizePolicy, QGridLayout, QLabel, QStackedWidget, 
                            QShortcut, QAction, QFrame)
from utils.win_tools import (hide_taskbar, kill_explorer, 
                           force_fullscreen_work_area, 
                           disable_task_manager, enable_task_manager)

def create_users_table():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT NOT NULL UNIQUE,
                      password TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def register_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        return False
    conn.close()
    return True

def authenticate_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    stored_password = cursor.fetchone()
    conn.close()
    return stored_password and stored_password[0] == password

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Регистрация")
        self.setFixedSize(885, 468)
        
        # Убираем рамку и делаем окно модальным без кнопок управления
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setModal(True)
        
        # Центрируем окно относительно родителя
        if parent:
            parent_rect = parent.frameGeometry()
            self.move(parent_rect.center() - self.rect().center())
        
        self.setStyleSheet("""
            background:#212121;
            color: white;
            font-size: 18px;
            border: none;
            border-radius: 0px;
        """)
        
        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Topbar
        topbar = QWidget()
        topbar.setFixedSize(885, 80)
        topbar.setStyleSheet("background-color: #121212;")
        
        # Лого в топбаре
        logo_label = QLabel(topbar)
        logo_label.setFixedSize(270, 150)
        logo_label.move((885 - 270) // 2, -35)  # Центрируем по горизонтали и немного поднимаем
        pixmap = QPixmap("images/logo.png")
        logo_label.setPixmap(pixmap.scaled(270, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        
        # Контентная область
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(50, 30, 50, 50)
        content_layout.setSpacing(20)

        title_label = QLabel("Регистрация")
        title_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #FFFFFF; 
            border:none; 
            border-radius:0px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Логин")
        self.username_input.setStyleSheet("""
            background: #5B5B5B;
            padding: 15px;
            border: none;
            font-size: 16px;
            color: white;
            border-radius:0px;
        """)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            background: #5B5B5B;
            padding: 15px;
            border: none;
            font-size: 16px;
            color: white;
            border-radius:0px;
        """)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Подтвердите пароль")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setStyleSheet("""
            background: #5B5B5B;
            padding: 15px;
            border: none;
            font-size: 16px;
            color: white;
            border-radius:0px;
        """)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        
        register_btn = QPushButton("Зарегистрироваться")
        register_btn.setStyleSheet("""
            QPushButton {
                background: #EAA21B;
                color: black;
                padding: 15px;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #F0B73D;
            }
        """)
        register_btn.clicked.connect(self.try_register)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #333333;
                color: white;
                padding: 15px;
                font-size: 16px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #444444;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(register_btn)
        buttons_layout.addWidget(cancel_btn)
        
        content_layout.addWidget(self.username_input)
        content_layout.addWidget(self.password_input)
        content_layout.addWidget(self.confirm_password_input)
        content_layout.addLayout(buttons_layout)
        
        # Добавляем элементы в главный layout
        main_layout.addWidget(topbar)
        main_layout.addWidget(content_widget)
        
        self.setLayout(main_layout)
    
    def try_register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Логин и пароль не могут быть пустыми!")
            return
            
        if len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать не менее 6 символов!")
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают!")
            return
            
        if register_user(username, password):
            QMessageBox.information(self, "Успех", "Регистрация успешна!")
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Логин уже существует!")


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setStyleSheet("background:#212121; color: white; font-size: 18px; border: none;")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()
        hide_taskbar()
        kill_explorer()
        force_fullscreen_work_area()
        disable_task_manager()

        # Topbar
        topbar = QWidget()
        topbar.setFixedSize(1920,106)
        topbar.setStyleSheet("background-color: #121212;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        main_layout.setAlignment(Qt.AlignCenter)
        
        self.auth_frame = QFrame()
        self.auth_frame.setFixedSize(875, 1080)
        self.auth_frame.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EAA21B, stop:1 #212121); border-radius: 0px; border:none;")

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(270, 150)
        self.logo_label.move(811, -22)
        self.logo_label.setParent(topbar)
        pixmap = QPixmap("images/logo.png")
        self.logo_label.setPixmap(pixmap.scaled(270, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setAlignment(Qt.AlignCenter)

        auth_wrapper = QHBoxLayout()
        auth_wrapper.setContentsMargins(0, 0, 0, 0)
        auth_wrapper.setSpacing(0)
        auth_wrapper.addStretch()  
        auth_wrapper.addWidget(self.auth_frame)

        auth_layout = QVBoxLayout()
        auth_layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel("Log in")
        title_label.setStyleSheet("color: black; font-size: 28px; background:none;")
        title_label.setContentsMargins(134,0,0,47)
        title_label.setAlignment(Qt.AlignLeft)
        auth_layout.addWidget(title_label)

        self.username_input = QLineEdit()
        self.username_input.setFixedSize(604,76)
        self.username_input.setPlaceholderText("Логин")
        self.username_input.setStyleSheet("background-color: #121212; padding: 28px; border: 2px solid; border-color: black; font-size: 15px;")

        self.password_input = QLineEdit()
        self.password_input.setFixedSize(604,76)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setStyleSheet("background-color: #121212; padding: 28px; border: 2px solid; border-color: black; font-size: 15px;")

        self.password_input.returnPressed.connect(self.login)
        self.username_input.returnPressed.connect(self.login)

        login_button = AnimatedButton()
        login_button.setIcon(QIcon("images/join_icon.png"))
        login_button.setIconSize(QSize(84,70))
        login_button.setFixedSize(84,70)
        login_button.setStyleSheet("background: none; border:none;")
        login_button.clicked.connect(self.login)

        register_button = QPushButton("Регистрация")
        register_button.setStyleSheet("""
            QPushButton {
                background: none; 
                color: #000000; 
                font-size: 16px;
                text-decoration: none;
            }
            QPushButton:hover {
                color: #EAA21B;
            }
        """)
        register_button.clicked.connect(self.show_register_dialog)

        username_wrapper = QHBoxLayout()
        username_wrapper.addStretch()
        username_wrapper.addWidget(self.username_input)
        username_wrapper.addStretch()
        username_wrapper.setContentsMargins(0,0,0,24)

        password_wrapper = QHBoxLayout()
        password_wrapper.addStretch()
        password_wrapper.addWidget(self.password_input)
        password_wrapper.addStretch()

        login_button_wrapper = QHBoxLayout()
        login_button_wrapper.addStretch()
        login_button_wrapper.addWidget(login_button)
        login_button_wrapper.setContentsMargins(0,13,0,0)
        login_button_wrapper.addStretch()

        register_button_wrapper = QHBoxLayout()
        register_button_wrapper.addStretch()
        register_button_wrapper.addWidget(register_button)
        register_button_wrapper.setAlignment(Qt.AlignRight)
        register_button_wrapper.setContentsMargins(0,10,125,0)

        auth_layout.addLayout(username_wrapper)
        auth_layout.addLayout(password_wrapper)
        auth_layout.addLayout(register_button_wrapper)
        auth_layout.addLayout(login_button_wrapper)

        self.auth_frame.setLayout(auth_layout)

        main_layout.addWidget(topbar)
        main_layout.addLayout(auth_wrapper)

        self._error_animation = None

    def show_register_dialog(self):
        dialog = RegisterDialog(self)
        dialog.exec_()

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if authenticate_user(username, password):
            self.accepted_login(username)
        else:
            self.auth_frame.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #AA2525, stop:1 #1B1B1B); border-radius: 0px; border:none;")
            QTimer.singleShot(500, self.reset_auth_frame_style)

    def accepted_login(self, username):
        with open("last_login.txt", "w") as f:
            f.write(username)

        self.close()
        subprocess.run(["main.exe", username])
 
    def closeEvent(self, event):
        enable_task_manager()
        from utils.win_tools import show_taskbar, start_explorer
        show_taskbar()
        start_explorer()
        
        # Заменяем попытку убить процесс на обычное закрытие
        event.accept()

    def reset_auth_frame_style(self):
        self.auth_frame.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #EAA21B, stop:1 #212121); border-radius: 0px; border:none;")

if __name__ == "__main__":
    create_users_table()
    app = QApplication(sys.argv)
    login_win = LoginWindow()
    login_win.show()
    sys.exit(app.exec_())