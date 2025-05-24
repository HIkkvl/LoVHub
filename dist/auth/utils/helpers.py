from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, QRect, QPropertyAnimation, QEasingCurve
import sqlite3
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
    db_path = "apps.db"
    if not os.path.exists(db_path):
        return [], []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, path, type, icon FROM apps")  
    rows = cursor.fetchall()
    conn.close()
    
    games = [{"id": row[0], "name": row[1], "path": row[2], "type": row[3], "icon": row[4]} for row in rows if row[3] == "game"]
    apps = [{"id": row[0], "name": row[1], "path": row[2], "type": row[3], "icon": row[4]} for row in rows if row[3] == "app"]
    
    return games, apps

def add_app_to_db(name, path, category, icon=None):
    try:
        db_path = "apps.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Приводим категорию к нижнему регистру и проверяем допустимые значения
        category = category.lower()
        if category not in ("game", "app"):
            category = "app"  # значение по умолчанию
            
        cursor.execute("INSERT INTO apps (name, path, type, icon) VALUES (?, ?, ?, ?)", 
                      (name, path, category, icon))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()


def delete_app_from_db(app_name):
    db_path = "apps.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apps WHERE name = ?", (app_name,))
    conn.commit()
    conn.close()
