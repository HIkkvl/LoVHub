# main.py
import sys
import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# Установка HiDPI ДО создания QApplication
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from windows.main_window import MainWindow

def main():
    if len(sys.argv) < 2:
        print("Error: No username provided")
        sys.exit(1)

    username = sys.argv[1]
    app = QApplication(sys.argv)
    window = MainWindow(app, username)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()