import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PyQt5.QtWidgets import QApplication
from windows.main_window import MainWindow


def main():
    if len(sys.argv) < 2:
        print("Error: No username provided")
        sys.exit(1)

    username = sys.argv[1]
    app = QApplication(sys.argv)
    window = MainWindow(app, username)  # Передаем username в MainWindow
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()