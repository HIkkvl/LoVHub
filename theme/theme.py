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

            /* ВАЖНО: ПЕРЕОПРЕДЕЛЯЕМ ПОСЛЕ ОБЩЕГО QWidget */
            QWidget#TopBar {
                background-color: #121212;
            }
        """
    else:  # light
        return """
            QWidget {
                background-color: #f0f0f0;
                color: #333;
                font-size: 18px;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """
