from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, QRect, QPropertyAnimation, QEasingCurve
import sqlite3
import requests
import json
import os
import uuid
import pythoncom
from win32com.client import Dispatch

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

def parse_steam_url_shortcut(url_path):
    """Парсим Steam .url файл и извлекаем AppID"""
    try:
        with open(url_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Ищем AppID в файле
            import re
            url_match = re.search(r'URL=steam://rungameid/(\d+)', content)
            if url_match:
                return url_match.group(1)
            
            # Альтернативный формат
            exe_match = re.search(r'Target=.*steam.exe.*-applaunch\s+(\d+)', content)
            if exe_match:
                return exe_match.group(1)
    except Exception as e:
        print(f"Ошибка чтения .url файла: {e}")
    return None

def parse_windows_shortcut(lnk_path):
    """Извлекает путь и аргументы из ярлыка Windows (.lnk)"""
    try:
        pythoncom.CoInitialize()  # Инициализация COM для работы с ярлыками
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        
        target = shortcut.TargetPath
        args = shortcut.Arguments
        
        # Если это Steam-ярлык, извлекаем AppID
        if "steam.exe" in target.lower():
            import re
            match = re.search(r'-applaunch\s+(\d+)', args)
            if match:
                return {
                    "type": "steam",
                    "path": f"steam://rungameid/{match.group(1)}",
                    "name": shortcut.Description,
                }
        
        # Обычный ярлык (программа или игра)
        return {
            "type": "app",
            "path": target + (" " + args if args else ""),
            "name": shortcut.Description or os.path.splitext(os.path.basename(lnk_path))[0],
        }
    except Exception as e:
        print(f"Ошибка чтения .lnk файла: {e}")
        return None
    finally:
        pythoncom.CoUninitialize()  # Освобождаем COM

def save_icon(file):
    """Сохраняет загруженную иконку в папку static/icons/ и возвращает имя файла"""
    upload_folder = 'static/icons/'
    
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    filename = f"{uuid.uuid4()}.png"  # Сохраняем как PNG для лучшего качества
    file_path = os.path.join(upload_folder, filename)
    
    # Если это QPixmap (из интерфейса)
    if isinstance(file, QPixmap):
        file.save(file_path)
    # Если это путь к файлу (из диалога выбора)
    elif isinstance(file, str):
        pixmap = QPixmap(file)
        pixmap.save(file_path)
    else:
        raise ValueError("Неподдерживаемый тип файла для иконки")
    
    return filename

def load_apps_from_db():
    try:
        # Мы используем API endpoint, который у тебя УЖЕ БЫЛ в server.py
        response = requests.get("http://localhost:5000/api/apps", timeout=3)
        response.raise_for_status() # Вызовет ошибку, если сервер ответил 4xx или 5xx
        
        apps_list = response.json()
        
        games = [app for app in apps_list if app.get("type") == "game"]
        apps = [app for app in apps_list if app.get("type") == "app"]
        
        return games, apps
    
    except requests.exceptions.RequestException as e:
        print(f"Ошибка: Не удалось загрузить приложения с сервера: {e}")
        # Возвращаем пустые списки, чтобы интерфейс не "упал"
        return [], []

def add_app_to_db(name, path, category, icon=None):
    """
    ЗАМЕНЯЕТ старую функцию. 
    Отправляет данные о новом приложении на сервер через API.
    """
    # 'icon' - это имя файла (например, 'uuid.png'), 
    # которое вернула функция save_icon()
    
    payload = {
        "name": name,
        "path": path,
        "type": category.lower(),
        "icon": icon 
    }
    
    try:
        # Используем новый API endpoint
        response = requests.post("http://localhost:5000/api/add_app", json=payload, timeout=3)
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") == "success":
            print(f"Приложение '{name}' успешно добавлено через API.")
        else:
            print(f"Ошибка API при добавлении приложения: {result.get('message')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Ошибка: Не удалось добавить приложение через API: {e}")
    except json.JSONDecodeError:
        print(f"Ошибка: Некорректный ответ от сервера: {response.text}")


def delete_app_from_db(app_name):
    """
    ЗАМЕНЯЕТ старую функцию.
    Отправляет команду на удаление на сервер через API.
    """
    payload = {"name": app_name}
    
    try:
        # Используем новый API endpoint
        response = requests.post("http://localhost:5000/api/delete_app", json=payload, timeout=3)
        response.raise_for_status()
        
        result = response.json()
        if result.get("status") == "success":
            print(f"Приложение '{app_name}' успешно удалено через API.")
        else:
            print(f"Ошибка API при удалении: {result.get('message')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Ошибка: Не удалось удалить приложение через API: {e}")
