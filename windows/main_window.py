from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, QScrollArea, 
                            QLabel, QGridLayout, QMessageBox, QInputDialog, 
                            QLineEdit, QShortcut, QSizePolicy,QPushButton)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QKeySequence
from PyQt5.QtCore import Qt, QTimer, QSize
from theme.theme import load_stylesheet
from core.app_launcher import AppLauncherThread
from core.taskbar_worker import TaskbarWorker
from utils.win_tools import (hide_taskbar, kill_explorer, 
                            force_fullscreen_work_area, 
                            disable_task_manager, enable_task_manager)
from utils.helpers import load_apps_from_db, AnimatedButton
from utils.network import send_app_launch_info
import win32gui
import win32con
import keyboard
import psutil
import os
import subprocess


def rounded_pixmap(pixmap, radius=12):
    size = pixmap.size()
    rounded = QPixmap(size)
    rounded.fill(Qt.transparent)

    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()

    return rounded


class MainWindow(QWidget):
    def __init__(self, app, username):
        super().__init__()
        self.app = app
        self.username = username
        self._is_authenticated = True  # Флаг авторизации
        self.current_theme = "dark"
        self.app.setStyleSheet(load_stylesheet(self.current_theme))

        self.known_hwnds = []
        hide_taskbar()
        force_fullscreen_work_area()
        disable_task_manager()

        self.setWindowTitle("Лаунчер")
        self.setStyleSheet("QPushButton { font-size: 16px; }")

        self.games, self.tools = load_apps_from_db()
        self.running_procs = []
        self.filtered_games = self.games.copy()
        self.filtered_apps = self.tools.copy()
        self.settings_open = False

        # Инициализация компонентов
        self.init_ui()
        self.init_timers()
        self.init_settings_window()  # Создаем окно настроек сразу

        # Подключаем сигнал завершения времени
        self.settings_window.time_expired.connect(self.handle_time_expired)
        
        # Горячие клавиши
        self.set_exit_hotkey()
        keyboard.add_hotkey('alt+shift', self.topbar.switch_language)

        # Запуск таймеров
        QTimer.singleShot(2000, self.taskbar_worker.start)

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        from windows.topbar import TopBar
        self.topbar = TopBar(self)
        main_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.create_page(self.games, "Games"))
        self.stack.addWidget(self.create_page(self.tools, "Applications"))
        main_layout.addWidget(self.stack)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setLayout(main_layout)
        self.showFullScreen()

    def init_timers(self):
        """Инициализация таймеров"""
        self.taskbar_worker = TaskbarWorker()
        self.taskbar_worker.update_icons.connect(self.update_taskbar_icons)

        self.tray_check_timer = QTimer()
        self.tray_check_timer.timeout.connect(self.update_custom_tray_apps)
        self.tray_check_timer.start(5000)

        self.taskbar_timer = QTimer(self)
        self.taskbar_timer.timeout.connect(self.taskbar_worker.start)
        self.taskbar_timer.start(3000)

        self.reload_timer = QTimer()
        self.reload_timer.timeout.connect(self.reload_apps_from_db)
        self.reload_timer.start(10000)

    def init_settings_window(self):
        """Инициализация окна настроек"""
        from windows.settings import SettingsWindow
        self.settings_window = SettingsWindow(self)
        # Таймеры уже запущены в конструкторе SettingsWindow

    def handle_time_expired(self):
        """Обработчик завершения времени"""
        # Восстанавливаем системные элементы
        enable_task_manager()
        from utils.win_tools import show_taskbar, start_explorer
        show_taskbar()
        start_explorer()
        
        # Закрываем текущее окно
        self.close()
        
        # Запускаем окно авторизации
        subprocess.Popen(["python", "auth.py"])
        
        # Завершаем текущее приложение
        self.app.quit()

        
    def open_settings_window(self):
        """Управление отображением окна настроек"""
        if self.settings_open:
            self.settings_window.close_with_animation()
            self.settings_open = False
        else:
            button_pos = self.topbar.settings_btn.mapToGlobal(
                self.topbar.settings_btn.rect().bottomRight())
            target_pos = button_pos - self.settings_window.rect().topRight()
            self.settings_window.show_with_animation(target_pos)
            self.settings_open = True

    def create_page(self, items, title):
        """Создает страницу с приложениями"""
        page_widget = QWidget()
        page_layout = QVBoxLayout(page_widget)
        page_layout.setAlignment(Qt.AlignTop)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(""" 
            QScrollArea { border: none; }
            QScrollBar:vertical, QScrollBar:horizontal { width: 0px; height: 0px; background: transparent; }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: transparent; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { background: transparent; }
        """)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        scroll_layout.addWidget(title_label)

        apps_layout = QGridLayout()
        apps_layout.setContentsMargins(120, 30, 120, 0)
        apps_layout.setSpacing(100)
        scroll_layout.addLayout(apps_layout)

        row, col, max_columns = 0, 0, 4
        for app in items:
            btn = AnimatedButton()
            btn.setFixedSize(334, 447)
            
            icon_filename = app.get('icon', None)
            icon_exists = icon_filename and os.path.exists(f"static/icons/{icon_filename}")

            icon_path = f"static/icons/{icon_filename}" if icon_exists else "static/icons/default_icon.png"

            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path).scaled(334, 447, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                rounded = rounded_pixmap(pixmap, 12)
                btn.setIcon(QIcon(rounded))
                btn.setIconSize(QSize(334, 447))

            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {'transparent' if icon_exists else 'white'};
                    border: none;
                    border-radius: 12px;
                    font-size: 20px;
                    text-align: center;
                    background: qlineargradient(
                        x1: 0, y1: 0,
                        x2: 0, y2: 1,
                        stop:0 #EAA21B, stop:1 #212121);
                }}
                QPushButton:hover {{
                    background-color: #EAA21B;
                }}
            """)

            btn.clicked.connect(lambda _, n=app["name"], p=app["path"]: self.run_app(n, p))
            apps_layout.addWidget(btn, row, col)
            col += 1
            if col >= max_columns:
                col = 0
                row += 1

        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area)
        return page_widget

    # Остальные методы класса остаются без изменений
    def update_taskbar_icons(self, hwnd_title_icon_list):
        hwnd_to_data = {hwnd: (title, icon) for hwnd, title, icon in hwnd_title_icon_list}
        current_hwnds = list(hwnd_to_data.keys())

        if not hasattr(self, "known_hwnds"):
            self.known_hwnds = []

        for hwnd in current_hwnds:
            if hwnd not in self.known_hwnds:
                self.known_hwnds.append(hwnd)

        self.known_hwnds = [hwnd for hwnd in self.known_hwnds if hwnd in current_hwnds and win32gui.IsWindow(hwnd)]

        for i in reversed(range(self.topbar.running_apps_container.count())):
            widget = self.topbar.running_apps_container.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for hwnd in self.known_hwnds:
            title, icon = hwnd_to_data[hwnd]
            btn = QPushButton()
            btn.setFixedSize(48, 48)
            btn.setToolTip(title)
            btn.setIcon(icon)
            btn.setIconSize(QSize(40, 40))
            btn.setStyleSheet("""
                QPushButton {
                    background:none;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
            """)
            btn.clicked.connect(lambda _, hwnd=hwnd: self.focus_and_toggle(hwnd))
            self.topbar.running_apps_container.addWidget(btn)

    def run_app(self, name, path):
        self.launcher_thread = AppLauncherThread(name, path)
        self.launcher_thread.finished.connect(self.on_app_launched)
        self.launcher_thread.error.connect(self.on_app_launch_error)
        self.launcher_thread.start()

    def on_app_launched(self, name, pid):
        self.running_procs.append((name, pid))
        send_app_launch_info(name)
        QTimer.singleShot(1500, self.taskbar_worker.start)

    def on_app_launch_error(self, message):
        QMessageBox.warning(self, "Ошибка запуска", f"Не удалось запустить приложение: {message}")

    def focus_and_toggle(self, hwnd):
        self.setFocus()
        QTimer.singleShot(50, lambda: self.toggle_hwnd(hwnd))

    def toggle_hwnd(self, hwnd):
        try:
            if not win32gui.IsWindow(hwnd):
                print(f"[DEBUG] hwnd {hwnd} больше не существует.")
                return

            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"[ERROR] toggle_hwnd: {e}")

    def set_exit_hotkey(self):
        shortcut = QShortcut(QKeySequence("Ctrl+Alt+P"), self)
        shortcut.activated.connect(self.ask_exit_password)

    def ask_exit_password(self):
        pwd, ok = QInputDialog.getText(self, "Выход", "Введите админ-пароль:", QLineEdit.Password)
        if ok and pwd == "1478":
            enable_task_manager()
            from utils.win_tools import show_taskbar, start_explorer
            show_taskbar()
            start_explorer()
            self.app.quit()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный пароль!")

    def switch_tab(self, index):
        if self.stack.currentIndex() != index:
            self.stack.setCurrentIndex(index)

    def update_search_results(self):
        search_text = self.topbar.search_input.text().lower()

        if not search_text:
            if self.stack.count() == 3:
                self.stack.removeWidget(self.stack.widget(2))
            self.stack.setCurrentIndex(self.stack.currentIndex())
            return

        combined = self.games + self.tools
        filtered = [item for item in combined if search_text in item[0].lower()]

        search_page = self.create_page(filtered, "Результаты поиска")

        if self.stack.count() == 3:
            self.stack.removeWidget(self.stack.widget(2))

        self.stack.addWidget(search_page)
        self.stack.setCurrentIndex(2)

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.app.setStyleSheet(load_stylesheet(self.current_theme))

    def reload_apps_from_db(self):
        self.games, self.tools = load_apps_from_db()
        self.filtered_games = self.games.copy()
        self.filtered_apps = self.tools.copy()

        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
            
        self.stack.addWidget(self.create_page(self.games, "Games"))
        self.stack.addWidget(self.create_page(self.tools, "Applications"))
        self.stack.setCurrentIndex(0)

    def update_custom_tray_apps(self):
        known_tray_apps = {
            "steam.exe": ("images/tray/steam_icon.png", lambda: print("Steam clicked")),
        }

        running = [p.name().lower() for p in psutil.process_iter()]
        
        self.topbar.clear_custom_tray()

        for exe_name, (icon_path, callback) in known_tray_apps.items():
            if exe_name in running:
                self.topbar.add_tray_icon(icon_path, exe_name.replace(".exe", "").capitalize(), callback)