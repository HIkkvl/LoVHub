from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QStackedWidget, QScrollArea, 
                            QLabel, QGridLayout, QMessageBox, QInputDialog, 
                            QLineEdit, QShortcut, QSizePolicy, QPushButton,
                            QGraphicsDropShadowEffect, QFrame,QCheckBox,QDialog)  
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QKeySequence, QColor
from PyQt5.QtCore import Qt, QTimer, QSize,QRect,QPoint
from theme.theme import load_stylesheet
from core.app_launcher import AppLauncherThread
from core.taskbar_worker import TaskbarWorker
from utils.win_tools import (hide_taskbar, kill_explorer, 
                            force_fullscreen_work_area, 
                            disable_task_manager, enable_task_manager)
from utils.helpers import parse_steam_url_shortcut, parse_windows_shortcut
from utils.helpers import load_apps_from_db, AnimatedButton
from utils.dialogs import AddAppDialog
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
        self.edit_mode = False
        self.selected_apps = set()
        screen = self.app.primaryScreen()
        screen_width = screen.size().width()
        
        if screen_width >= 3840:  # 4K
            self.scale_factor = 2.0
        elif screen_width >= 2560:  # 2K
            self.scale_factor = 1.5
        elif screen_width >= 1920:  # FullHD
            self.scale_factor = 1.0
        else:  # HD и меньше
            self.scale_factor = 0.8

        self._is_authenticated = True  # Флаг авторизации
        self.current_theme = "dark"
        self.app.setStyleSheet(load_stylesheet(self.current_theme))

        self.known_hwnds = []
        hide_taskbar()
        force_fullscreen_work_area()
        disable_task_manager()

        # Применяем масштаб ко всему приложению
        self.app.setAttribute(Qt.AA_EnableHighDpiScaling)
        self.app.setAttribute(Qt.AA_UseHighDpiPixmaps)

        self.setWindowTitle("Лаунчер")
        self.setStyleSheet(f"QPushButton {{ font-size: {int(16 * self.scale_factor)}px; }}")

        self.games, self.tools = load_apps_from_db()
        self.running_procs = []
        self.filtered_games = self.games.copy()
        self.filtered_apps = self.tools.copy()
        self.settings_open = False

        self.init_ui()
        self.init_timers()
        self.init_settings_window()  

        self.settings_window.time_expired.connect(self.handle_time_expired)
        

        self.set_exit_hotkey()
        keyboard.add_hotkey('alt+shift', self.topbar.switch_language)

        # Запуск таймеров
        QTimer.singleShot(2000, self.taskbar_worker.start)

    def closeEvent(self, event):
        event.ignore()


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

    def handle_time_expired(self):
        """Обработчик завершения времени"""
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
            btn.setFixedSize(int(334 * self.scale_factor), int(447 * self.scale_factor))

            # Контейнер для иконки и чекбокса
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

            # Иконка
            icon_filename = app.get('icon', None)
            icon_exists = icon_filename and os.path.exists(f"static/icons/{icon_filename}")
            icon_path = f"static/icons/{icon_filename}" if icon_exists else "static/icons/default_icon.png"

            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path).scaled(int(334 * self.scale_factor), int(447 * self.scale_factor), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
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
                    background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #EAA21B, stop:1 #212121);
                }}
                QPushButton:hover {{
                    background-color: #EAA21B;
                }}
            """)

            if self.edit_mode:
                checkbox = QCheckBox()
                checkbox.setChecked(app["name"] in self.selected_apps)
                checkbox.setStyleSheet("QCheckBox::indicator { width: 24px; height: 24px; }")
                
                container_layout.addWidget(checkbox, alignment=Qt.AlignTop | Qt.AlignRight)
                
                def on_checkbox_clicked(state, app_name=app["name"]):
                    if state:
                        self.selected_apps.add(app_name)
                    else:
                        self.selected_apps.discard(app_name)
                
                checkbox.stateChanged.connect(on_checkbox_clicked)
                
                def on_button_clicked():
                    checkbox.setChecked(not checkbox.isChecked())
                
                btn.clicked.connect(on_button_clicked)
            else:
                btn.clicked.connect(lambda _, n=app["name"], p=app["path"]: self.run_app(n, p))

            btn.setLayout(container_layout)
            apps_layout.addWidget(btn, row, col)

            col += 1
            if col >= max_columns:
                col = 0
                row += 1

        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area)
        return page_widget

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


    def open_add_app_dialog(self):
        if not hasattr(self, 'add_btn'):
            print("Warning: add_btn attribute not found in MainWindow when opening AddAppDialog. Using fallback geometry.")
            button_geometry = QRect(self.mapToGlobal(QPoint(10, 70)), QSize(40,40)) 
        else:
            button_global_pos = self.add_btn.mapToGlobal(QPoint(0, 0))
            button_geometry = QRect(button_global_pos, self.add_btn.size())
        
        topbar_abs_rect = None
        if hasattr(self, 'topbar') and self.topbar.isVisible():
            topbar_abs_rect = QRect(self.topbar.mapToGlobal(QPoint(0,0)), self.topbar.size())

        admin_panel_abs_rect = None
        if hasattr(self, 'admin_panel') and self.admin_panel.isVisible():
            admin_panel_abs_rect = QRect(self.admin_panel.mapToGlobal(QPoint(0,0)), self.admin_panel.size())
        
        dialog = AddAppDialog(self, button_geometry, topbar_abs_rect, admin_panel_abs_rect)
        
        dialog.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1: 0, y1: 0,x2: 0, y2: 1,stop:0 #202020, stop:1 #121212);
                border: none;
                border-radius: 0px;
                color: white; 
            }
            QLabel {
                color: white;
                font-size: 14px; 
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px; 
            }
            QGroupBox {
                color: white;
                font-size: 14px; 
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
                left: 10px; 
            }
            QRadioButton {
                color: white;
                font-size: 14px; 
            }
            QPushButton {
                background-color: #EAA21B;
                color: #212121; 
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-size: 14px; 
            }
            QPushButton:hover {
                background-color: #F0B232; 
            }
            QPushButton:pressed {
                background-color: #D49007; 
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(dialog)
        shadow.setBlurRadius(32)
        shadow.setXOffset(9)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 64))
        dialog.setGraphicsEffect(shadow)
        
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            icon_filename = None
            if data["icon"]:
                try:
                    from utils.helpers import save_icon
                    icon_filename = save_icon(data["icon"])
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить иконку: {e}")
            
            from utils.helpers import add_app_to_db
            add_app_to_db(data["name"], data["path"], data["type"], icon_filename)
            
            self.reload_apps_from_db()

            
    def run_app(self, name, path):
        try:
            if path.startswith('steam://'):
                self.run_steam_game(name, path)  
            else:
                self.launcher_thread = AppLauncherThread(name, path)
                self.launcher_thread.finished.connect(self.on_app_launched)
                self.launcher_thread.error.connect(self.on_app_launch_error)
                self.launcher_thread.start()
            
            send_app_launch_info(name)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка запуска", f"Не удалось запустить: {str(e)}")

    def run_steam_game(self, name, steam_url):
        """Запускает игру через Steam, игнорируя ложные ошибки"""
        try:
            import subprocess
            import time
            
            subprocess.Popen(["start", steam_url], shell=True)
            
            time.sleep(3)
            

            game_running = self.check_if_game_running(name)
            if not game_running:
                QMessageBox.warning(self, "Ошибка", "Игра не запустилась. Попробуйте еще раз.")
            
        except Exception as e:
            print(f"[Steam] Ошибка запуска: {e}")

    def check_if_game_running(self, name):
        """Проверяет, запущен ли процесс игры (для Steam-игр)"""
        try:
            for proc in psutil.process_iter(['name']):
                if name.lower() in proc.info['name'].lower():
                    return True
            return False
        except:
            return False  


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
            if not hasattr(self, 'admin_panel'):
                self.init_admin_panel()
            
            # Переключаем видимость панели
            if self.admin_panel.isVisible():
                self.admin_panel.hide()
                self.edit_mode = False
                self.selected_apps.clear()
                self.reload_apps_from_db()
            else:
                self.admin_panel.show()
                self.edit_mode = True
                self.selected_apps.clear()
                self.reload_apps_from_db()
        else:   
            QMessageBox.warning(self, "Ошибка", "Неверный пароль!")

    def init_admin_panel(self):
        """Инициализация панели администратора с иконками внизу"""
        self.admin_panel = QFrame(self)
        self.admin_panel.setObjectName("Admin_panel")
        
        
        # Настройка тени
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(32.9)
        shadow.setXOffset(9)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 64))
        self.admin_panel.setGraphicsEffect(shadow)
        self.admin_panel.setFixedWidth(105)
        
        topbar_height = self.topbar.height() if hasattr(self, 'topbar') else 0
        panel_height = self.height() - topbar_height
        self.admin_panel.setFixedHeight(panel_height)
        self.admin_panel.move(0, topbar_height)
        self.admin_panel.hide()

        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 20)
        main_layout.setSpacing(15)
        
       
    
        self.add_btn = AnimatedButton(self.admin_panel)
        self.add_btn.setToolTip("Добавить приложение")
        self.add_btn.setFixedSize(40, 40)
        self.add_btn.setIconSize(QSize(32, 32))
        add_icon_path = "images/add_icon.png"
        if os.path.exists(add_icon_path):
            self.add_btn.setIcon(QIcon(add_icon_path))
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3a3;
                border-radius: 3px;
            }
        """)
        self.add_btn.clicked.connect(self.open_add_app_dialog)
        main_layout.addWidget(self.add_btn, alignment=Qt.AlignCenter)

        
        delete_btn = AnimatedButton(self.admin_panel)
        delete_btn.setToolTip("Удалить выбранные приложения")
        delete_btn.setFixedSize(40, 40)
        delete_btn.setIconSize(QSize(32, 32))
        delete_icon_path = "images/delete_icon.png"
        if os.path.exists(delete_icon_path):
            delete_btn.setIcon(QIcon(delete_icon_path))
        delete_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #933;
                border-radius: 3px;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_apps)
        main_layout.addWidget(delete_btn, alignment=Qt.AlignCenter)

        # Добавляем распорку, чтобы оставшиеся кнопки были внизу
        main_layout.addStretch()

        # Кнопка диспетчера задач
        taskmgr_btn = AnimatedButton(self.admin_panel)
        taskmgr_icon_path = "images/taskmanager_icon.png"
        if os.path.exists(taskmgr_icon_path):
            taskmgr_icon = QIcon(taskmgr_icon_path)
            taskmgr_btn.setIcon(taskmgr_icon)
            taskmgr_btn.setIconSize(QSize(32, 32))
        taskmgr_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #333;
                border-radius: 3px;
            }
        """)
        taskmgr_btn.setFixedSize(40, 40)
        taskmgr_btn.setToolTip("Открыть диспетчер задач")
        taskmgr_btn.clicked.connect(lambda: subprocess.Popen("taskmgr", shell=True))
        main_layout.addWidget(taskmgr_btn, alignment=Qt.AlignCenter)

        # Кнопка выхода
        exit_btn = AnimatedButton(self.admin_panel)
        exit_icon_path = "images/exit_icon.png"
        if os.path.exists(exit_icon_path):
            exit_icon = QIcon(exit_icon_path)
            exit_btn.setIcon(exit_icon)
            exit_btn.setIconSize(QSize(32, 32))
        exit_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #333;
                border-radius: 3px;
            }
        """)
        exit_btn.setFixedSize(40, 40)
        exit_btn.setToolTip("Выйти из режима администратора")
        exit_btn.clicked.connect(self.clean_exit)
        main_layout.addWidget(exit_btn, alignment=Qt.AlignCenter)

        self.admin_panel.setLayout(main_layout)

        # Обработчики событий видимости
        def showEvent(event):
            enable_task_manager()
            super(self.admin_panel.__class__, self.admin_panel).showEvent(event)
        
        def hideEvent(event):
            disable_task_manager()
            super(self.admin_panel.__class__, self.admin_panel).hideEvent(event)
        
        self.admin_panel.showEvent = showEvent
        self.admin_panel.hideEvent = hideEvent

    def clean_exit(self):
        """Корректный выход из системы"""
        enable_task_manager()  # Убедимся, что диспетчер задач разблокирован
        from utils.win_tools import show_taskbar, start_explorer
        show_taskbar()
        start_explorer()
        self.app.quit()

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
        filtered = [item for item in combined if search_text in item['name'].lower()]

        search_page = self.create_page(filtered, "Результаты поиска")

        if self.stack.count() == 3:
            self.stack.removeWidget(self.stack.widget(2))

        self.stack.addWidget(search_page)
        self.stack.setCurrentIndex(2)

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.app.setStyleSheet(load_stylesheet(self.current_theme))

    def delete_selected_apps(self):
        if not self.selected_apps:
            QMessageBox.information(self, "Удаление", "Ничего не выбрано.")
            return

        from utils.helpers import delete_app_from_db
        for app_name in self.selected_apps:
            delete_app_from_db(app_name)

        self.selected_apps.clear()
        self.reload_apps_from_db()

    def get_steam_shortcut_info(lnk_path):
        """Извлекает информацию о Steam-игре из ярлыка"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(lnk_path)
            
            # Проверяем, что это Steam-ярлык
            if "steam.exe" in shortcut.TargetPath.lower():
                import re
                # Извлекаем AppID из аргументов
                match = re.search(r'-applaunch\s+(\d+)', shortcut.Arguments)
                if match:
                    return {
                        'app_id': match.group(1),
                        'name': shortcut.Description,
                        'target': shortcut.TargetPath,
                        'args': shortcut.Arguments
                    }
        except Exception as e:
            print(f"Ошибка чтения ярлыка: {e}")
        return None

    def reload_apps_from_db(self):
        # Запоминаем текущую вкладку
        current_index = self.stack.currentIndex()
        
        # Обновляем данные
        self.games, self.tools = load_apps_from_db()
        self.filtered_games = self.games.copy()
        self.filtered_apps = self.tools.copy()

        # Удаляем старые виджеты
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
            
        # Создаем новые страницы
        self.stack.addWidget(self.create_page(self.games, "Games"))
        self.stack.addWidget(self.create_page(self.tools, "Applications"))
        
        # Восстанавливаем предыдущую вкладку, но не выходим за пределы количества вкладок
        if current_index < self.stack.count():
            self.stack.setCurrentIndex(current_index)
        else:
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