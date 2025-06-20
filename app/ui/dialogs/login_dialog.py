"""
Login Dialog
============
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QCheckBox, QFrame, QMessageBox
)

from app.core.auth import get_session_manager
from app.core.logger import get_logger
from app.core.exceptions import AuthenticationException, ValidationException
from app.core.error_handler import error_handler_decorator, handle_error

logger = get_logger(__name__)


class LoginDialog(QDialog):
    """Kullanıcı giriş dialog'u"""
    
    login_successful = pyqtSignal(dict)  # User dict emit eder
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_manager = get_session_manager()
        self._setup_ui()
        self._load_users()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        self.setWindowTitle("WMS - Kullanıcı Girişi")
        self.setFixedSize(400, 300)
        self.setModal(True)
        
        # Ana layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Logo/Title area
        self._create_header(layout)
        
        # Login form
        self._create_login_form(layout)
        
        # Buttons
        self._create_buttons(layout)
        
        # Info label
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.info_label)
        
        # Focus
        self.username_combo.setFocus()
    
    def _create_header(self, layout):
        """Header alanı oluştur"""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("Depo Yönetim Sistemi")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        subtitle_label = QLabel("Kullanıcı Girişi")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                font-size: 12px;
                background: transparent;
            }
        """)
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        layout.addWidget(header_frame)
    
    def _create_login_form(self, layout):
        """Login formu oluştur"""
        form_frame = QFrame()
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(15)
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Kullanıcı:")
        username_label.setMinimumWidth(80)
        
        self.username_combo = QComboBox()
        self.username_combo.setEditable(True)
        self.username_combo.setMinimumHeight(30)
        
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_combo)
        form_layout.addLayout(username_layout)
        
        # Password (şimdilik placeholder)
        password_layout = QHBoxLayout()
        password_label = QLabel("Şifre:")
        password_label.setMinimumWidth(80)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(30)
        self.password_input.setPlaceholderText("Şifrenizi girin (admin: hakan14)")
        
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        form_layout.addLayout(password_layout)
        
        # Remember me
        self.remember_checkbox = QCheckBox("Beni hatırla")
        form_layout.addWidget(self.remember_checkbox)
        
        layout.addWidget(form_frame)
        
        # Enter key handling
        self.username_combo.lineEdit().returnPressed.connect(self._attempt_login)
        self.password_input.returnPressed.connect(self._attempt_login)
    
    def _create_buttons(self, layout):
        """Butonları oluştur"""
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton("Giriş Yap")
        self.login_button.setMinimumHeight(35)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.login_button.clicked.connect(self._attempt_login)
        
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.login_button)
        
        layout.addLayout(button_layout)
    
    @error_handler_decorator("Kullanıcı listesi yüklenemedi", show_toast=True)
    def _load_users(self):
        """Kullanıcı listesini yükle"""
        users = self.session_manager.user_manager.get_all_users()
        active_users = [user for user in users if user.is_active]
        
        for user in active_users:
            self.username_combo.addItem(
                f"{user.full_name} ({user.username})",
                user.username
            )
        
        self.info_label.setText(f"{len(active_users)} aktif kullanıcı")
    
    def _attempt_login(self):
        """Login denemesi"""
        # Username al (combo'dan seçili olan veya yazılan)
        if self.username_combo.currentData():
            username = self.username_combo.currentData()
        else:
            username = self.username_combo.currentText().strip()
        
        password = self.password_input.text()
        
        if not username:
            QMessageBox.warning(self, "Hata", "Kullanıcı adı gerekli!")
            return
        
        try:
            # Login dene
            if self.session_manager.login(username, password):
                user = self.session_manager.get_current_user()
                logger.info(f"Login successful: {user.username}")
                
                # Success signal emit et
                self.login_successful.emit(user.to_dict())
                self.accept()
                
        except (AuthenticationException, ValidationException) as e:
            # Structured error handling
            handle_error(e, show_dialog=True, parent=self)
            
        except Exception as e:
            # Beklenmeyen hatalar
            handle_error(
                e, 
                "Giriş sırasında beklenmeyen hata oluştu", 
                show_dialog=True, 
                parent=self
            )
    
    def get_login_info(self):
        """Login bilgilerini al (static method gibi kullanım için)"""
        dialog = LoginDialog()
        if dialog.exec_() == QDialog.Accepted:
            return dialog.session_manager.get_current_user()
        return None


class UserSwitchDialog(QDialog):
    """Kullanıcı değiştirme dialog'u"""
    
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.session_manager = get_session_manager()
        self._setup_ui()
    
    def _setup_ui(self):
        """UI'ı kur"""
        self.setWindowTitle("Kullanıcı Değiştir")
        self.setFixedSize(300, 200)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Current user info
        current_info = QLabel(f"Mevcut: {self.current_user.full_name}")
        current_info.setStyleSheet("font-weight: bold; color: #2c3e50;")
        layout.addWidget(current_info)
        
        # New user selection
        layout.addWidget(QLabel("Yeni kullanıcı:"))
        
        self.user_combo = QComboBox()
        users = self.session_manager.user_manager.get_all_users()
        for user in users:
            if user.is_active and user.username != self.current_user.username:
                self.user_combo.addItem(
                    f"{user.full_name} ({user.role})",
                    user.username
                )
        layout.addWidget(self.user_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        switch_button = QPushButton("Değiştir")
        switch_button.clicked.connect(self._switch_user)
        
        cancel_button = QPushButton("İptal")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(switch_button)
        
        layout.addLayout(button_layout)
    
    def _switch_user(self):
        """Kullanıcı değiştir"""
        if self.user_combo.currentData():
            new_username = self.user_combo.currentData()
            
            # Logout current user
            self.session_manager.logout()
            
            # Login new user
            if self.session_manager.login(new_username):
                self.accept()
            else:
                QMessageBox.warning(self, "Hata", "Kullanıcı değiştirilemedi!")
        else:
            QMessageBox.warning(self, "Hata", "Kullanıcı seçin!")