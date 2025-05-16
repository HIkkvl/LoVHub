def load_stylesheet(theme="dark"):
    if theme == "dark":
        return """
            QWidget {
                background-color: #212121;
                color: white;
                font-size: 18px;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }

            QWidget#TopBar {
                background-color: #121212;
            }
            QWidget#TaskBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #252525, stop:1 #121212);
            }
            QLineEdit#Search {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #252525, stop:1 #121212);
                font-size: 16px;
                border: none;
            }
            QWidget#Settings
            {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #212121, stop:1 #171717);
            }
        """
    else:  # light
        return """
            QWidget {
                background-color: #BCBABA;
                color: #333;
                font-size: 18px;
            }
            QPushButton {
                background-color: #D9D9D9;
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QWidget#TopBar {
                background-color: #878686;
            }
            QWidget#TaskBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BCBABA, stop:1 #878686);
            }
            QLineEdit#Search {
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BCBABA, stop:1 #878686);
                font-size: 16px;
                border: none;
            }
            QWidget#Setting
            {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #BCBABA, stop:1 #A1A1A1);
            }
        """
