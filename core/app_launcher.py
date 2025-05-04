from PyQt5.QtCore import QThread, pyqtSignal
import subprocess
import os


class AppLauncherThread(QThread):
    finished = pyqtSignal(str, int)  # name, pid
    error = pyqtSignal(str)

    def __init__(self, name, path):
        super().__init__()
        self.name = name
        self.path = path

    def run(self):
        try:
            if not os.path.exists(self.path):
                raise FileNotFoundError(f"Файл не найден: {self.path}")
            proc = subprocess.Popen([self.path])
            self.finished.emit(self.name, proc.pid)
        except Exception as e:
            self.error.emit(str(e))
