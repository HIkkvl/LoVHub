from PyQt5.QtGui import QIcon
from PyQt5.QtWinExtras import QtWin
import win32gui
import os


def extract_icon_from_exe(path):
    try:
        if not os.path.exists(path):
            return QIcon()

        large, _ = win32gui.ExtractIconEx(path, 0)
        if large:
            hicon = large[0]
            pixmap = QtWin.fromHICON(hicon)
            win32gui.DestroyIcon(hicon)
            if pixmap:
                return QIcon(pixmap)
    except Exception as e:
        print(f"[ERROR] Не удалось извлечь иконку из {path}: {e}")
    return QIcon()
