"""
Add User Dialog
==============

Yeni kullanıcı ekleme dialog'u.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QCheckBox, QFormLayout, QMessageBox
)

from app.core.auth import get_session_manager
from app.core.logger import get_logger, log_user_action
from app.core.exceptions import ValidationException
from app.core.error_handler import error_handler_decorator

logger = get_logger(__name__)


class AddUserDialog(QDialog):
    """Yeni kullanıcı ekleme dialog'u"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_manager = get_session_manager()
        self._setup_ui()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        self.setWindowTitle("Yeni Kullanıcı Ekle")
        self.setModal(True)
        self.resize(400, 350)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Yeni Kullanıcı Ekle")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
                text-align: center;
            }
        """)
        layout.addWidget(header_label)
        
        # Form
        form_layout = QFormLayout()
        
        # Username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Benzersiz kullanıcı adı")
        form_layout.addRow("Kullanıcı Adı*:", self.username_edit)
        
        # Full name
        self.fullname_edit = QLineEdit()
        self.fullname_edit.setPlaceholderText("Kullanıcının tam adı")
        form_layout.addRow("Tam Ad*:", self.fullname_edit)
        
        # Email
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("kullanici@example.com")
        form_layout.addRow("E-posta:", self.email_edit)
        
        # Password
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("En az 4 karakter")
        form_layout.addRow("Şifre*:", self.password_edit)
        
        # Confirm password
        self.confirm_password_edit = QLineEdit()
        self.confirm_password_edit.setEchoMode(QLineEdit.Password)
        self.confirm_password_edit.setPlaceholderText("Şifreyi tekrar girin")
        form_layout.addRow("Şifre Tekrar*:", self.confirm_password_edit)
        
        # Role
        self.role_combo = QComboBox()
        self.role_combo.addItems(["operator", "scanner", "admin"])
        self.role_combo.setCurrentText("operator")  # Default role
        form_layout.addRow("Rol:", self.role_combo)
        
        # Warehouse
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.addItems(["0 - Genel", "1 - Ana Depo", "2 - Yan Depo"])
        form_layout.addRow("Depo:", self.warehouse_combo)
        
        # Active
        self.active_checkbox = QCheckBox("Aktif")
        self.active_checkbox.setChecked(True)
        form_layout.addRow("", self.active_checkbox)
        
        layout.addLayout(form_layout)
        
        # Info label
        info_label = QLabel("* işaretli alanlar zorunludur")
        info_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("Kullanıcı Oluştur")
        self.create_btn.clicked.connect(self._create_user)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        
        cancel_btn = QPushButton("İptal")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
        
        # Enter key handling
        self.username_edit.returnPressed.connect(self._create_user)
        self.fullname_edit.returnPressed.connect(self._create_user)
        self.email_edit.returnPressed.connect(self._create_user)
        self.password_edit.returnPressed.connect(self._create_user)
        self.confirm_password_edit.returnPressed.connect(self._create_user)
    
    @error_handler_decorator("Kullanıcı oluşturulamadı", show_dialog=True)
    def _create_user(self):
        """Yeni kullanıcı oluştur"""
        
        # Form verilerini al
        username = self.username_edit.text().strip()
        fullname = self.fullname_edit.text().strip()
        email = self.email_edit.text().strip()
        password = self.password_edit.text()
        confirm_password = self.confirm_password_edit.text()
        role = self.role_combo.currentText()
        warehouse_id = int(self.warehouse_combo.currentText().split(" ")[0])
        is_active = self.active_checkbox.isChecked()
        
        # Validasyonlar
        self._validate_form(username, fullname, password, confirm_password)
        
        # Kullanıcı verisi
        user_data = {
            'username': username,
            'full_name': fullname,
            'email': email,
            'password': password,
            'role': role,
            'warehouse_id': warehouse_id,
            'is_active': is_active
        }
        
        # Kullanıcı oluştur
        new_user = self.session_manager.user_manager.add_user(user_data)
        
        # Success
        QMessageBox.information(
            self, 
            "Başarılı", 
            f"Kullanıcı '{new_user.full_name}' başarıyla oluşturuldu!\n\n"
            f"Kullanıcı Adı: {new_user.username}\n"
            f"Rol: {new_user.role}"
        )
        
        log_user_action(
            "USER_CREATE",
            f"New user created: {new_user.username}",
            target_user=new_user.username,
            role=new_user.role,
            warehouse_id=new_user.warehouse_id
        )
        
        self.accept()
    
    def _validate_form(self, username, fullname, password, confirm_password):
        """Form validasyonu"""
        
        # Zorunlu alanlar
        if not username:
            raise ValidationException("Kullanıcı adı gerekli", field="username")
        
        if not fullname:
            raise ValidationException("Tam ad gerekli", field="fullname")
        
        if not password:
            raise ValidationException("Şifre gerekli", field="password")
        
        # Username format kontrolü
        if len(username) < 3:
            raise ValidationException("Kullanıcı adı en az 3 karakter olmalı", field="username")
        
        if not username.replace('_', '').replace('-', '').isalnum():
            raise ValidationException("Kullanıcı adı sadece harf, rakam, _ ve - içerebilir", field="username")
        
        # Şifre kontrolü
        if len(password) < 4:
            raise ValidationException("Şifre en az 4 karakter olmalı", field="password")
        
        if password != confirm_password:
            raise ValidationException("Şifreler eşleşmiyor", field="confirm_password")
        
        # Kullanıcı adı benzersizliği
        existing_user = self.session_manager.user_manager.get_user(username)
        if existing_user:
            raise ValidationException(f"'{username}' kullanıcı adı zaten kullanılıyor", field="username")