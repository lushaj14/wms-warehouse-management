"""
Kullanıcı Yönetimi Sayfası
=========================
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)

from app.core.auth import get_session_manager, get_current_user
from app.core.logger import get_logger, log_user_action


class UserPage(QWidget):
    """Kullanıcı yönetimi sayfası"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.session_manager = get_session_manager()
        self._setup_ui()
        self._load_users()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Kullanıcı Yönetimi")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Admin kontrolü
        current_user = self.session_manager.get_current_user()
        if current_user and current_user.role == "admin":
            add_user_btn = QPushButton("Yeni Kullanıcı Ekle")
            add_user_btn.clicked.connect(self._add_user)
            header_layout.addWidget(add_user_btn)
        
        layout.addLayout(header_layout)
        
        # Kullanıcı tablosu
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels([
            "Kullanıcı Adı", "Tam Ad", "E-posta", "Rol", "Durum", "Son Giriş"
        ])
        
        # Tablo ayarları
        header = self.user_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.user_table)
        
        # Alt butonlar
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        refresh_btn = QPushButton("Yenile")
        refresh_btn.clicked.connect(self._load_users)
        button_layout.addWidget(refresh_btn)
        
        layout.addLayout(button_layout)
    
    def _load_users(self):
        """Kullanıcıları yükle"""
        try:
            users = self.session_manager.user_manager.get_all_users()
            
            self.user_table.setRowCount(len(users))
            
            for row, user in enumerate(users):
                # Kullanıcı adı
                self.user_table.setItem(row, 0, QTableWidgetItem(user.username))
                
                # Tam ad
                self.user_table.setItem(row, 1, QTableWidgetItem(user.full_name))
                
                # E-posta
                self.user_table.setItem(row, 2, QTableWidgetItem(user.email or ""))
                
                # Rol
                role_item = QTableWidgetItem(user.role)
                if user.role == "admin":
                    role_item.setBackground(Qt.lightGray)
                self.user_table.setItem(row, 3, role_item)
                
                # Durum
                status_text = "Aktif" if user.is_active else "Pasif"
                status_item = QTableWidgetItem(status_text)
                if user.is_active:
                    status_item.setBackground(Qt.green)
                else:
                    status_item.setBackground(Qt.red)
                self.user_table.setItem(row, 4, status_item)
                
                # Son giriş
                last_login = user.last_login or "Hiçbir zaman"
                if user.last_login:
                    # ISO formatını daha okunabilir hale getir
                    last_login = user.last_login[:19].replace('T', ' ')
                self.user_table.setItem(row, 5, QTableWidgetItem(last_login))
            
            log_user_action("USER_LIST_VIEWED", f"{len(users)} kullanıcı listelendi")
            
        except Exception as e:
            self.logger.error(f"Error loading users: {e}")
            QMessageBox.warning(self, "Hata", f"Kullanıcılar yüklenemedi: {str(e)}")
    
    def _add_user(self):
        """Yeni kullanıcı ekleme dialog'unu aç"""
        try:
            from app.ui.dialogs.user_management_dialog import UserManagementDialog
            dialog = UserManagementDialog(self)
            if dialog.exec_():
                self._load_users()  # Listeyi yenile
        except ImportError:
            QMessageBox.information(
                self, 
                "Bilgi", 
                "Kullanıcı yönetimi dialog'u henüz mevcut değil."
            )
    
    def apply_settings(self):
        """Ayarları uygula (main_window tarafından çağrılır)"""
        pass