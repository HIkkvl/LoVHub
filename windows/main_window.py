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
from utils.helpers import parse_steam_url_shortcut, parse_windows_shortcut, AnimatedButton
from utils.dialogs import AddAppDialog
from utils.network import send_app_launch_info
from utils.workers import LoadAppsWorker, AddAppWorker, DeleteAppsWorker

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
        
        if screen_width >= 3840:
            self.scale_factor = 2.0
        elif screen_width >= 2560:
            self.scale_factor = 1.5
        elif screen_width >= 1920:
            self.scale_factor = 1.0
        else:
            self.scale_factor = 0.8

        self._is_authenticated = True
        self.current_theme = "dark"
        self.app.setStyleSheet(load_stylesheet(self.current_theme))

        self.known_hwnds = []
        hide_taskbar()
        force_fullscreen_work_area()
        disable_task_manager()

        self.setWindowTitle("Лаунчер")
        self.setStyleSheet(f"QPushButton {{ font-size: {int(16 * self.scale_factor)}px; }}")

        self.games = []
        self.tools = []
        self.app_load_worker = None
        self.workers = []
        
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

        QTimer.singleShot(2000, self.taskbar_worker.start)

        self.reload_apps_from_db()

    def closeEvent(self, event):
        event.ignore()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        from windows.topbar import TopBar
        self.topbar = TopBar(self)
        main_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()
        self.stack.addWidget(QWidget())
        self.stack.addWidget(QWidget())
        
        main_layout.addWidget(self.stack)
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setLayout(main_layout)
        self.showFullScreen()

    def init_timers(self):
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
        from windows.settings import SettingsWindow
        self.settings_window = SettingsWindow(self)

    def handle_time_expired(self):
        enable_task_manager()
        from utils.win_tools import show_taskbar, start_explorer
        show_taskbar()
        start_explorer()
        
        self.close()
        subprocess.Popen(["py", "auth.py"])
        self.app.quit()
        
    def open_settings_window(self):
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
        
        if not items:
             pass 
        else:
            for app in items:
                btn = AnimatedButton()
                btn.setFixedSize(int(334 * self.scale_factor), int(447 * self.scale_factor))

                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(0, 0, 0, 0)
                container_layout.setSpacing(0)

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
            
            print(f"Запускаем AddAppWorker для {data['name']}...")
            worker = AddAppWorker(
                data["name"], 
                data["path"], 
                data["type"], 
                icon_filename
            )
            
            worker.finished.connect(self.on_app_added)
            worker.error.connect(self.on_app_add_error)
            
            self.workers.append(worker)
            worker.finished.connect(lambda: self.workers.remove(worker))
            worker.error.connect(lambda: self.workers.remove(worker))
            
            worker.start()

    def on_app_added(self, app_name):
        print(f"Приложение '{app_name}' успешно добавлено.")
        QMessageBox.information(self, "Успех", f"Приложение '{app_name}' добавлено.")
        self.reload_apps_from_db()

    def on_app_add_error(self, error_message):
        print(f"Ошибка добавления приложения: {error_message}")
        QMessageBox.warning(self, "Ошибка", f"Не удалось добавить приложение:\n{error_message}")
            
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
        try:
            import subprocess
            import time
            
            subprocess.Popen(["start", steam_url], shell=True)
            
            time.sleep(3)

            game_running = self.check_if_game_running(name)
            if not game_running:
                QMessageBox.warning(self, "Ошибка", "Игра не запустилась. Попробуйте еще раз.")
            
        except Exception as e:
            print(f"Ошибка запуска Steam: {e}")

    def check_if_game_running(self, name):
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
                return

            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"Ошибка переключения окна: {e}")

    def set_exit_hotkey(self):
        shortcut = QShortcut(QKeySequence("Ctrl+Alt+P"), self)
        shortcut.activated.connect(self.ask_exit_password)

    def ask_exit_password(self):
        pwd, ok = QInputDialog.getText(self, "Выход", "Введите админ-пароль:", QLineEdit.Password)
        if ok and pwd == "1478":
            if not hasattr(self, 'admin_panel'):
                self.init_admin_panel()
            
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
        self.admin_panel = QFrame(self)
        self.admin_panel.setObjectName("Admin_panel")
        
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

        main_layout.addStretch()

        taskmgr_btn = AnimatedButton(self.admin_panel)
        taskmgr_icon_path = "images/taskmanager_icon.png"
        if os.path.exists(taskmgr_icon_path):
            taskmgr_btn.setIcon(QIcon(taskmgr_icon_path))
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

        exit_btn = AnimatedButton(self.admin_panel)
        exit_icon_path = "images/exit_icon.png"
        if os.path.exists(exit_icon_path):
            exit_btn.setIcon(QIcon(exit_icon_path))
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

        def showEvent(event):
            enable_task_manager()
            super(self.admin_panel.__class__, self.admin_panel).showEvent(event)
        
        def hideEvent(event):
            disable_task_manager()
            super(self.admin_panel.__class__, self.admin_panel).hideEvent(event)
        
        self.admin_panel.showEvent = showEvent
        self.admin_panel.hideEvent = hideEvent

    def clean_exit(self):
        enable_task_manager()
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
            
        app_list = list(self.selected_apps)
        print(f"Запускаем DeleteAppsWorker для {len(app_list)} приложений...")
        
        worker = DeleteAppsWorker(app_list)
        worker.finished.connect(self.on_apps_deleted)
        worker.error.connect(self.on_apps_delete_error)
        
        self.workers.append(worker)
        worker.finished.connect(lambda: self.workers.remove(worker))
        worker.error.connect(lambda: self.workers.remove(worker))
        
        worker.start()

    def on_apps_deleted(self, deleted_list, failed_list):
        print(f"Удалено: {len(deleted_list)}, Ошибки: {len(failed_list)}")
        
        if failed_list:
            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить: {', '.join(failed_list)}")
        else:
            QMessageBox.information(self, "Успех", f"Успешно удалено {len(deleted_list)} приложений.")
            
        self.selected_apps.clear()
        self.reload_apps_from_db()

    def on_apps_delete_error(self, error_message):
        print(f"Ошибка удаления приложений: {error_message}")
        QMessageBox.warning(self, "Ошибка", f"Не удалось удалить приложения:\n{error_message}")

    def reload_apps_from_db(self):
        print("Запрос на обновление приложений... (запуск worker)")
        if self.app_load_worker and self.app_load_worker.isRunning():
            print("Worker все еще занят, пропускаем.")
            return 
            
        self.app_load_worker = LoadAppsWorker()
        
        self.app_load_worker.finished.connect(self.on_apps_loaded)
        self.app_load_worker.error.connect(self.on_apps_load_error)
        
        self.app_load_worker.start()

    def on_apps_loaded(self, games, apps):
        print("Приложения успешно загружены!")
        current_index = self.stack.currentIndex()
        
        is_search_active = (current_index == 2)
        
        self.games = games
        self.tools = apps
        self.filtered_games = self.games.copy()
        self.filtered_apps = self.tools.copy()

        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()
            
        self.stack.addWidget(self.create_page(self.games, "Games"))
        self.stack.addWidget(self.create_page(self.tools, "Applications"))
        
        if is_search_active:
            self.update_search_results()
            self.stack.setCurrentIndex(2)
        elif current_index < self.stack.count():
            self.stack.setCurrentIndex(current_index)
        else:
            self.stack.setCurrentIndex(0)
            
        self.app_load_worker = None

    def on_apps_load_error(self, error_message):
        print(f"Ошибка воркера: {error_message}")
        QMessageBox.warning(self, "Ошибка сети", f"Не удалось обновить список приложений:\n{error_message}")
        self.app_load_worker = None
    
    def update_custom_tray_apps(self):
        known_tray_apps = {
            "steam.exe": ("images/tray/steam_icon.png", lambda: print("Steam clicked")),
        }

        running = [p.name().lower() for p in psutil.process_iter()]
        
        self.topbar.clear_custom_tray()

        for exe_name, (icon_path, callback) in known_tray_apps.items():
            if exe_name in running:
                self.topbar.add_tray_icon(icon_path, exe_name.replace(".exe", "").capitalize(), callback)