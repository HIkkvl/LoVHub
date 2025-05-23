from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QHBoxLayout,
    QMessageBox, QGroupBox, QRadioButton
)
from PyQt5.QtCore import Qt, QPoint, QRect
import os


class AddAppDialog(QDialog):
    def __init__(self, parent=None, button_geometry=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить приложение")
        self.setFixedSize(429, 748)

        # Сохраняем геометрию кнопки как атрибут класса
        self.button_geometry = button_geometry if button_geometry else QRect()

        # Убираем кнопки свернуть/закрыть и делаем окно модальным
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.Popup)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 15, 15, 15)

        # Название
        self.layout.addWidget(QLabel("Название:"))
        self.name_input = QLineEdit()
        self.layout.addWidget(self.name_input)

        # Группа для выбора типа
        self.type_group = QGroupBox("Тип приложения:")
        type_layout = QHBoxLayout()

        self.game_radio = QRadioButton("Игра")
        self.app_radio = QRadioButton("Приложение")
        self.app_radio.setChecked(True)

        type_layout.addWidget(self.game_radio)
        type_layout.addWidget(self.app_radio)
        self.type_group.setLayout(type_layout)
        self.layout.addWidget(self.type_group)

        # Выбор ярлыка
        self.layout.addWidget(QLabel("Путь к программе:"))
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)

        self.browse_path_btn = QPushButton("Выбрать...")
        self.browse_path_btn.clicked.connect(self.browse_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_path_btn)
        self.layout.addWidget(QLabel("Выберите .exe, .lnk или Steam .url файл"))
        self.layout.addLayout(path_layout)

        # Выбор иконки
        self.layout.addWidget(QLabel("Иконка (опционально):"))
        self.icon_input = QLineEdit()
        self.icon_input.setReadOnly(True)

        self.browse_icon_btn = QPushButton("Выбрать...")
        self.browse_icon_btn.clicked.connect(self.browse_icon)

        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_input)
        icon_layout.addWidget(self.browse_icon_btn)
        self.layout.addWidget(QLabel("Рекомендуемый размер: 334x447 px"))
        self.layout.addLayout(icon_layout)

        # Кнопки
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.validate_and_accept)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(buttons_layout)

        self.setLayout(self.layout)

    def showEvent(self, event):
        """Позиционируем окно справа от кнопки"""
        if self.button_geometry and self.parent():
            button_pos = self.parent().mapToGlobal(self.button_geometry.bottomRight())

            dialog_x = button_pos.x() - self.width() // 2
            dialog_y = button_pos.y() - self.height()

            screen_geometry = self.screen().availableGeometry()
            if dialog_x + self.width() > screen_geometry.right():
                dialog_x = screen_geometry.right() - self.width()
            if dialog_y < screen_geometry.top():
                dialog_y = screen_geometry.top()

            self.move(QPoint(dialog_x, dialog_y))

        super().showEvent(event)

    def browse_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите программу или ярлык",
            "",
            "Программы (*.exe);;Ярлыки (*.lnk *.url);;Все файлы (*.*)"
        )

        if path:
            self.path_input.setText(path)

            if not self.name_input.text():
                name = os.path.splitext(os.path.basename(path))[0]
                self.name_input.setText(name)

            if path.endswith(".url") or "steam.exe" in path.lower():
                self.game_radio.setChecked(True)

    def browse_icon(self):
        icon_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите иконку",
            "",
            "Изображения (*.png *.jpg *.jpeg)"
        )

        if icon_path:
            self.icon_input.setText(icon_path)

    def validate_and_accept(self):
        if not self.name_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите название приложения!")
            return

        if not self.path_input.text():
            QMessageBox.warning(self, "Ошибка", "Выберите путь к программе!")
            return

        self.accept()

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "type": "game" if self.game_radio.isChecked() else "app",
            "path": self.path_input.text(),
            "icon": self.icon_input.text() or None
        }
