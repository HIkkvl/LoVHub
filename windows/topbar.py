from PyQt5.QtWidgets import (
    QWidget, QLineEdit, QPushButton, QLabel, QToolButton,
    QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, QSize, QTime, QDate
from utils.helpers import AnimatedButton
import win32api
import locale
from PyQt5.QtWidgets import QDialog

class TopBar(QFrame):
    def __init__(self, main_window):
        super().__init__()
        self.setObjectName("TopBar")
        self.main_window = main_window
        self.scale_factor = main_window.scale_factor
        self.setFixedSize(int(1920 * self.scale_factor), int(106 * self.scale_factor))
        self.tray_expanded = False  # флаг состояния кастомного трея

        self.setup_search()
        self.setup_buttons()
        self.setup_clock()
        self.setup_language()
        self.setup_logo()
        self.setup_custom_tray()
        self.setup_taskbar_panel()

    def setup_search(self):
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setObjectName("Search")
        self.search_input.setFixedSize(int(480 * self.scale_factor), int(60 * self.scale_factor))
        self.search_input.move(int(20 * self.scale_factor), int(23 * self.scale_factor))
        self.search_input.textChanged.connect(self.main_window.update_search_results)

        search_icon = QToolButton(self.search_input)
        search_icon.setIcon(QIcon("images/search_icon.png"))
        search_icon.setIconSize(QSize(int(32 * self.scale_factor), int(32 * self.scale_factor)))
        search_icon.setStyleSheet("border: none; background: none;")
        search_icon.setCursor(Qt.PointingHandCursor)
        search_icon.resize(int(40 * self.scale_factor), int(40 * self.scale_factor))
        search_icon.move(int(10 * self.scale_factor), int(10 * self.scale_factor))
        self.search_input.setTextMargins(int(50 * self.scale_factor), 0, 0, 0)


    def setup_buttons(self):
        # Кнопка "Games"
        self.games_btn = AnimatedButton(self)
        self.games_btn.setIcon(QIcon("images/games_icon.png"))
        self.settings_btn.setIconSize(QSize(int(64 * self.scale_factor), int(64 * self.scale_factor)))
        self.games_btn.setFixedSize(64, 64)
        self.games_btn.move(618, 21)
        self.games_btn.setStyleSheet("background: none; border: none;")
        self.games_btn.clicked.connect(lambda: self.main_window.switch_tab(0))

        # Кнопка "Apps"
        self.apps_btn = AnimatedButton(self)
        self.apps_btn.setIcon(QIcon("images/apps_icon.png"))
        self.settings_btn.setIconSize(QSize(int(64 * self.scale_factor), int(64 * self.scale_factor)))
        self.apps_btn.setFixedSize(64, 64)
        self.apps_btn.move(727, 21)
        self.apps_btn.setStyleSheet("background: none; border: none;")
        self.apps_btn.clicked.connect(lambda: self.main_window.switch_tab(1))

        self.tray_toggle_btn = QPushButton("˄", self)
        self.tray_toggle_btn.setFixedSize(30, 30)
        self.tray_toggle_btn.move(1557, 40)
        self.tray_toggle_btn.setStyleSheet("""
            QPushButton {
                color: white;
                font-size: 18px;
                background-color: none;
                border: none;
            }
            QPushButton:hover {
                background-color: #666;
                border-radius: 4px;
            }
        """)
        self.tray_toggle_btn.clicked.connect(self.toggle_custom_tray)

        self.settings_btn = QPushButton(self)
        self.settings_btn.setIcon(QIcon("images/user_icon.png"))
        self.settings_btn.setIconSize(QSize(int(64 * self.scale_factor), int(64 * self.scale_factor)))
        self.settings_btn.setFixedSize(64, 64)
        self.settings_btn.move(1837, 21)
        self.settings_btn.setStyleSheet("background:none; border: none;")
        self.settings_btn.clicked.connect(self.main_window.open_settings_window)

    def setup_custom_tray(self):
        self.custom_tray_widget = QDialog(self)
        self.custom_tray_widget.setWindowFlags(Qt.Popup)
        self.custom_tray_widget.setFixedSize(200, 50)
        self.custom_tray_widget.setStyleSheet("background-color: #222; border-radius: 6px;")

        self.custom_tray_layout = QHBoxLayout(self.custom_tray_widget)
        self.custom_tray_layout.setContentsMargins(5, 5, 5, 5)
        self.custom_tray_layout.setSpacing(10)


    def add_tray_icon(self, icon_path, tooltip, callback):
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(28, 28))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
            }
            QPushButton:hover {
                background-color: #444;
                border-radius: 4px;
            }
        """)
        btn.clicked.connect(callback)
        self.custom_tray_layout.addWidget(btn)

    def toggle_custom_tray(self):
        if self.tray_expanded:
            self.custom_tray_widget.hide()
            self.tray_toggle_btn.setText("˄")
        else:
            btn_global_pos = self.tray_toggle_btn.mapToGlobal(self.tray_toggle_btn.rect().bottomLeft())

            self.custom_tray_widget.move(btn_global_pos.x(), btn_global_pos.y() + 5)
            self.custom_tray_widget.show()
            self.tray_toggle_btn.setText("˅")
        
        self.tray_expanded = not self.tray_expanded


    def setup_clock(self):
        self.time_label = QLabel(self)
        self.time_label.setStyleSheet("color: white; font-size: 36px; background:none;")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setFixedSize(108, 47)
        self.time_label.move(1700, 20)

        self.date_label = QLabel(self)
        self.date_label.setStyleSheet("color: white; font-size: 20px; background:none;")
        self.date_label.setAlignment(Qt.AlignRight)
        self.date_label.setFixedSize(108, 25)
        self.date_label.move(1690, 55)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

    def update_time(self):
        time_text = QTime.currentTime().toString("HH:mm")
        date_text = QDate.currentDate().toString("dd.MM.yyyy")
        self.time_label.setText(time_text)
        self.date_label.setText(date_text)

    def setup_language(self):
        self.lang_label = QLabel("RU", self)
        self.lang_label.setStyleSheet("color: white; font-size: 26px; background:none;")
        self.lang_label.setFixedSize(60, 40)
        self.lang_label.setAlignment(Qt.AlignCenter)
        self.lang_label.move(1599, 33)

        self.lang_timer = QTimer()
        self.lang_timer.timeout.connect(self.update_language_label)
        self.lang_timer.start(1000)

    def update_language_label(self):
        layout = win32api.GetKeyboardLayout(0)
        language_code = hex(layout & (2**16 - 1))
        lang = locale.windows_locale.get(int(language_code, 16), 'Unknown')
        short_lang = lang.split('_')[0].upper()
        self.lang_label.setText(short_lang)

    def switch_language(self):
        import keyboard
        keyboard.press_and_release('alt+shift')

    def setup_logo(self):
        logo = QLabel(self)
        pix = QPixmap("images/logo.png")
        if not pix.isNull():
            pix = pix.scaled(270, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo.setPixmap(pix)
            logo.move(821, -22)
            logo.setFixedSize(270, 150)
            logo.setStyleSheet("background:none;")
            logo.setAlignment(Qt.AlignCenter)
        else:
            logo.setText("LOGO")
            logo.setStyleSheet("color: red; font-size: 20px;")
            logo.move(950, 13)

    def setup_taskbar_panel(self):
        self.running_apps_widget = QWidget(self)
        self.running_apps_widget.setObjectName("TaskBar")
        self.running_apps_widget.setFixedSize(400, 80)
        self.running_apps_widget.move(1091, 13)

        self.running_apps_container = QHBoxLayout(self.running_apps_widget)
        self.running_apps_container.setAlignment(Qt.AlignLeft)
        self.running_apps_container.setContentsMargins(8, 0, 0, 0)
        self.running_apps_container.setSpacing(5)

    def clear_custom_tray(self):
        while self.custom_tray_layout.count():
            child = self.custom_tray_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
