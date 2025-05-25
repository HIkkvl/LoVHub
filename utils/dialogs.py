from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QHBoxLayout,
    QMessageBox, QGroupBox, QRadioButton,QSizePolicy
)
from PyQt5.QtCore import Qt, QPoint, QRect,QSize
from PyQt5.QtGui import QIcon, QPixmap
import os


class AddAppDialog(QDialog):
    def __init__(self, parent=None, button_geometry=None, topbar_rect=None, admin_panel_rect=None): 
        super().__init__(parent)
        self.setWindowTitle("Add Games")
        self.setFixedSize(429, 748) 

        self.selected_icon_path = None
        
        self.button_geometry = button_geometry if button_geometry else QRect()
        self.topbar_rect = topbar_rect if topbar_rect else QRect() 
        self.admin_panel_rect = admin_panel_rect 
        
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint) 
        self.setWindowModality(Qt.ApplicationModal)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 15, 15, 15) 

        # Заголовок с прозрачным фоном
        title_label = QLabel("Add Games")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px; 
                font-weight: bold;
                background: transparent;
                color: white;
            }
        """)
        self.layout.addWidget(title_label)
        self.layout.addSpacing(20)

        # Кнопка добавления изображения с фиксированным размером
        self.add_image_btn = QPushButton("add image")
        self.add_image_btn.setFixedSize(QSize(334, 447))
        self.add_image_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.add_image_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(234, 162, 27, 0.21),
                stop:1 rgba(71, 62, 45, 0.97)
            );
                border:none;                
                font-size: 16px;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(234, 162, 27, 0.3),
                stop:1 rgba(71, 62, 45, 1)
            );
            }
        """)
        self.add_image_btn.clicked.connect(self.browse_icon)
        self.layout.addWidget(self.add_image_btn, alignment=Qt.AlignCenter)
        self.layout.addSpacing(20)

        # Название игры с прозрачным фоном
        name_label = QLabel("Name Game")
        name_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                background: transparent;
                color: white;
            }
        """)
        self.layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setStyleSheet("font-size: 14px;")
        self.layout.addWidget(self.name_input)
        self.layout.addSpacing(20)

        # Путь к игре с прозрачным фоном
        path_label = QLabel("Path to the game")
        path_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                background: transparent;
                color: white;
            }
        """)
        self.layout.addWidget(path_label)
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setStyleSheet("font-size: 14px;")

        self.browse_path_btn = QPushButton("Выбрать...")
        self.browse_path_btn.setStyleSheet("font-size: 14px;")
        self.browse_path_btn.clicked.connect(self.browse_path)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_path_btn)
        self.layout.addLayout(path_layout)
        self.layout.addSpacing(20)


        # Скрытая группа для выбора типа
        self.type_group = QGroupBox("Тип приложения:")
        type_layout = QHBoxLayout()

        self.game_radio = QRadioButton("Игра")
        self.app_radio = QRadioButton("Приложение")
        self.app_radio.setChecked(True)

        type_layout.addWidget(self.game_radio)
        type_layout.addWidget(self.app_radio)
        self.type_group.setLayout(type_layout)
        self.type_group.hide()
        self.layout.addWidget(self.type_group)

        # Кнопки
        self.add_btn = QPushButton("Добавить")
        self.add_btn.setStyleSheet("font-size: 14px;")
        self.add_btn.clicked.connect(self.validate_and_accept)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet("font-size: 14px;")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch() 
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(buttons_layout)

        self.setLayout(self.layout)

    def showEvent(self, event):
        """Позиционируем окно, избегая топ-бара и админ-панели"""
        if not (self.button_geometry and self.button_geometry.isValid() and self.parent()):
            super().showEvent(event) 
            return

        button_rect = self.button_geometry 
        dialog_w = self.width()
        dialog_h = self.height()
        
        screen_geom = self.screen().availableGeometry() 


        effective_min_x = screen_geom.left()
        if self.admin_panel_rect and self.admin_panel_rect.isValid():
            effective_min_x = max(effective_min_x, self.admin_panel_rect.right() + 5) 


        effective_min_y = screen_geom.top()
        if self.topbar_rect and self.topbar_rect.isValid():
            effective_min_y = max(effective_min_y, self.topbar_rect.bottom() + 5) 


        dialog_x = button_rect.right() + 5
        

        if (dialog_x + dialog_w > screen_geom.right()) or (dialog_x < effective_min_x):

            dialog_x_left_attempt = button_rect.left() - dialog_w - 5
            
            if (dialog_x_left_attempt >= effective_min_x) and \
               (dialog_x_left_attempt >= screen_geom.left()): 
                dialog_x = dialog_x_left_attempt
            else:
                dialog_x = effective_min_x
        

        if dialog_x < effective_min_x:
            dialog_x = effective_min_x
        

        if dialog_x + dialog_w > screen_geom.right():
            dialog_x = screen_geom.right() - dialog_w

            if dialog_x < effective_min_x:
                dialog_x = effective_min_x


        dialog_y = button_rect.top()

        if dialog_y < effective_min_y:
            dialog_y = effective_min_y
        
        if dialog_y + dialog_h > screen_geom.bottom():
            dialog_y = screen_geom.bottom() - dialog_h
        
    
        if dialog_y < effective_min_y:
            dialog_y = effective_min_y 
            
        self.move(QPoint(int(dialog_x), int(dialog_y))) 
            
        super().showEvent(event)


    def browse_path(self):
        """Открывает диалог выбора файла (.exe, .lnk, .url)"""
        file_dialog = QFileDialog(self) 
        file_dialog.setWindowTitle("Выберите программу или ярлык")
        file_dialog.setNameFilter("Программы (*.exe);;Ярлыки (*.lnk *.url);;Все файлы (*.*)")
        

        file_dialog.setWindowModality(Qt.WindowModal) # 
        
        if file_dialog.exec_(): 
            files = file_dialog.selectedFiles()
            if files:
                path = files[0]
                self.path_input.setText(path)
                
                if not self.name_input.text():
                    name = os.path.splitext(os.path.basename(path))[0]
                    self.name_input.setText(name)
                
                if path.endswith(".url") or ("steam.exe" in path.lower()):
                    self.game_radio.setChecked(True)

    def browse_icon(self):
        icon_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Выберите иконку",
            "",
            "Изображения (*.png *.jpg *.jpeg)"
        )

        if icon_path:
            self.selected_icon_path = icon_path  


            pixmap = QPixmap(icon_path).scaled(self.add_image_btn.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.add_image_btn.setIcon(QIcon(pixmap))
            self.add_image_btn.setIconSize(self.add_image_btn.size())
            self.add_image_btn.setText("")  

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
            "icon": self.selected_icon_path
        }
