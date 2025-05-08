from PyQt5.QtCore import QThread, pyqtSignal
import win32gui
import win32con
import win32process
import os
from utils.icons import extract_icon_from_exe
from utils.win_tools import get_exe_path_from_pid  # будем определять отдельно, если понадобится
from PyQt5.QtGui import QIcon


class TaskbarWorker(QThread):
    update_icons = pyqtSignal(list)  # Список: [(hwnd, title, icon)]

    def run(self):
        def is_valid_window(hwnd):
            if not win32gui.IsWindowVisible(hwnd):
                return False
            if not win32gui.IsWindowEnabled(hwnd):
                return False
            title = win32gui.GetWindowText(hwnd)
            if not title or title.strip() == "":
                return False
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if not (style & win32con.WS_CAPTION) or not (style & win32con.WS_SYSMENU):
                return False
            return True

        result = []

        def handle(hwnd, _):
            if not is_valid_window(hwnd):
                return

            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            exe_path = get_exe_path_from_pid(pid)
            if not exe_path or not os.path.exists(exe_path):
                return

            icon = extract_icon_from_exe(exe_path)

            if icon.isNull():
                return

            result.append((hwnd, title, icon))

        win32gui.EnumWindows(handle, None)
        self.update_icons.emit(result)
