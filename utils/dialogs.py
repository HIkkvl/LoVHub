from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QHBoxLayout, QMessageBox
import os

class AddAppDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить приложение")
        self.setFixedSize(400, 300)
        
        self.layout = QVBoxLayout()
        
        # Название
        self.layout.addWidget(QLabel("Название:"))
        self.name_input = QLineEdit()
        self.layout.addWidget(self.name_input)
        
        # Выбор ярлыка (.exe, .lnk, .url)
        self.layout.addWidget(QLabel("Путь к программе:"))
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        
        self.browse_path_btn = QPushButton("Выбрать...")
        self.browse_path_btn.clicked.connect(self.browse_path)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_path_btn)
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
        self.layout.addLayout(icon_layout)
        
        # Кнопки "Добавить" и "Отмена"
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.validate_and_accept)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(buttons_layout)
        
        self.setLayout(self.layout)
    
    def browse_path(self):
        """Открывает диалог выбора файла (.exe, .lnk, .url)"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите программу или ярлык",
            "",
            "Программы (*.exe);;Ярлыки (*.lnk *.url);;Все файлы (*.*)"
        )
        
        if path:
            self.path_input.setText(path)
            
            # Автоматически заполняем название, если оно пустое
            if not self.name_input.text():
                name = os.path.splitext(os.path.basename(path))[0]
                self.name_input.setText(name)
    
    def browse_icon(self):
        """Открывает диалог выбора иконки (PNG, JPG)"""
        icon_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите иконку",
            "",
            "Изображения (*.png *.jpg *.jpeg)"
        )
        
        if icon_path:
            self.icon_input.setText(icon_path)
    
    def validate_and_accept(self):
        """Проверяет, заполнены ли обязательные поля"""
        if not self.name_input.text():
            QMessageBox.warning(self, "Ошибка", "Введите название приложения!")
            return
        
        if not self.path_input.text():
            QMessageBox.warning(self, "Ошибка", "Выберите путь к программе!")
            return
        
        self.accept()
    
    def get_data(self):
        """Возвращает данные в виде словаря"""
        return {
            "name": self.name_input.text(),
            "path": self.path_input.text(),
            "icon": self.icon_input.text() if self.icon_input.text() else None
        }