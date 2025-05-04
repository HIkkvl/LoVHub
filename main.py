import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PyQt5.QtWidgets import QApplication
from windows.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow(app)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
