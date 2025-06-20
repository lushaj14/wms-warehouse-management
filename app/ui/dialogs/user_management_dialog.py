"""
User Management Dialog
=====================

Kullanıcı yönetimi için admin panel dialog'u.
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QGroupBox, QFormLayout, QMessageBox,
    QSplitter, QFrame, QTextEdit
)

from app.core.auth import get_session_manager, has_permission
from app.core.logger import get_logger, log_user_action
from app.core.exceptions import ValidationException, AuthenticationException
from app.core.error_handler import error_handler_decorator, handle_error

logger = get_logger(__name__)


class UserManagementDialog(QDialog):
    """Kullanıcı yönetimi dialog'u"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session_manager = get_session_manager()
        self.selected_user = None
        
        # Yetki kontrolü
        if not has_permission("admin"):
            QMessageBox.warning(self, "Yetki Hatası", "Bu işlem için admin yetkisi gerekli!")
            self.reject()
            return
        
        self._setup_ui()
        self._load_users()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        self.setWindowTitle("Kullanıcı Yönetimi")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Kullanıcı Yönetimi")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        layout.addWidget(header_label)
        
        # Main content - splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Sol panel - kullanıcı listesi
        self._create_users_list(splitter)
        
        # Sağ panel - kullanıcı detayları
        self._create_user_details(splitter)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)
        
        # Bottom buttons
        self._create_buttons(layout)
    
    def _create_users_list(self, parent):
        """Kullanıcı listesi paneli"""
        list_frame = QFrame()
        list_layout = QVBoxLayout(list_frame)
        
        # Title
        list_title = QLabel("Kullanıcı Listesi")
        list_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        list_layout.addWidget(list_title)
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Ara:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Kullanıcı adı veya tam ad...")
        self.search_input.textChanged.connect(self._filter_users)
        search_layout.addWidget(self.search_input)
        list_layout.addLayout(search_layout)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["Kullanıcı Adı", "Tam Ad", "Rol", "Durum"])
        
        header = self.users_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.users_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.users_table.itemSelectionChanged.connect(self._user_selected)
        list_layout.addWidget(self.users_table)
        
        # Add user button
        add_user_btn = QPushButton("Yeni Kullanıcı Ekle")
        add_user_btn.clicked.connect(self._add_new_user)
        list_layout.addWidget(add_user_btn)
        
        parent.addWidget(list_frame)
    
    def _create_user_details(self, parent):
        """Kullanıcı detayları paneli"""
        details_frame = QFrame()
        details_layout = QVBoxLayout(details_frame)
        
        # Title
        details_title = QLabel("Kullanıcı Detayları")
        details_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addWidget(details_title)
        
        # User form
        form_group = QGroupBox("Kullanıcı Bilgileri")
        form_layout = QFormLayout(form_group)
        
        self.username_edit = QLineEdit()
        self.fullname_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Yeni şifre (boş bırakılabilir)")
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "operator", "scanner"])
        
        self.warehouse_combo = QComboBox()
        self.warehouse_combo.addItems(["0 - Genel", "1 - Ana Depo", "2 - Yan Depo"])
        
        self.active_checkbox = QCheckBox("Aktif")
        
        form_layout.addRow("Kullanıcı Adı:", self.username_edit)
        form_layout.addRow("Tam Ad:", self.fullname_edit)
        form_layout.addRow("E-posta:", self.email_edit)
        form_layout.addRow("Şifre:", self.password_edit)
        form_layout.addRow("Rol:", self.role_combo)
        form_layout.addRow("Depo:", self.warehouse_combo)
        form_layout.addRow("", self.active_checkbox)
        
        details_layout.addWidget(form_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Kaydet")
        self.save_btn.clicked.connect(self._save_user)
        self.save_btn.setEnabled(False)
        
        self.delete_btn = QPushButton("Sil")
        self.delete_btn.clicked.connect(self._delete_user)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; }")
        
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.delete_btn)
        action_layout.addStretch()
        
        details_layout.addLayout(action_layout)
        
        # Activity log
        log_group = QGroupBox("Son Aktiviteler")
        log_layout = QVBoxLayout(log_group)
        
        self.activity_log = QTextEdit()
        self.activity_log.setMaximumHeight(150)
        self.activity_log.setReadOnly(True)
        log_layout.addWidget(self.activity_log)
        
        details_layout.addWidget(log_group)
        
        details_layout.addStretch()
        parent.addWidget(details_frame)
    
    def _create_buttons(self, layout):
        """Alt butonlar"""
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Yenile")
        refresh_btn.clicked.connect(self._load_users)
        
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    @error_handler_decorator("Kullanıcılar yüklenemedi", show_toast=True)
    def _load_users(self):
        """Kullanıcı listesini yükle"""
        users = self.session_manager.user_manager.get_all_users()
        
        self.users_table.setRowCount(len(users))
        
        for i, user in enumerate(users):
            self.users_table.setItem(i, 0, QTableWidgetItem(user.username))
            self.users_table.setItem(i, 1, QTableWidgetItem(user.full_name))
            self.users_table.setItem(i, 2, QTableWidgetItem(user.role))
            
            status = "Aktif" if user.is_active else "Deaktif"
            status_item = QTableWidgetItem(status)
            if not user.is_active:
                status_item.setBackground(Qt.lightGray)
            self.users_table.setItem(i, 3, status_item)
            
            # User data'yı row'a ekle
            self.users_table.item(i, 0).setData(Qt.UserRole, user)
        
        logger.info(f"Loaded {len(users)} users")
    
    def _filter_users(self):
        """Kullanıcı listesini filtrele"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.users_table.rowCount()):
            username = self.users_table.item(row, 0).text().lower()
            fullname = self.users_table.item(row, 1).text().lower()
            
            visible = search_text in username or search_text in fullname
            self.users_table.setRowHidden(row, not visible)
    
    def _user_selected(self):
        """Kullanıcı seçildiğinde"""
        current_row = self.users_table.currentRow()
        if current_row >= 0:
            user_item = self.users_table.item(current_row, 0)
            if user_item:
                self.selected_user = user_item.data(Qt.UserRole)
                self._populate_user_form()
                self.save_btn.setEnabled(True)
                self.delete_btn.setEnabled(self.selected_user.username != "admin")
    
    def _populate_user_form(self):
        """Seçili kullanıcının bilgilerini forma doldur"""
        if not self.selected_user:
            return
        
        user = self.selected_user
        
        self.username_edit.setText(user.username)
        self.fullname_edit.setText(user.full_name)
        self.email_edit.setText(user.email or "")
        self.password_edit.clear()  # Şifre gösterilmez
        
        # Rol seç
        role_index = self.role_combo.findText(user.role)
        if role_index >= 0:
            self.role_combo.setCurrentIndex(role_index)
        
        # Depo seç
        warehouse_index = self.warehouse_combo.findText(f"{user.warehouse_id} -", Qt.MatchStartsWith)
        if warehouse_index >= 0:
            self.warehouse_combo.setCurrentIndex(warehouse_index)
        
        self.active_checkbox.setChecked(user.is_active)
        
        # Activity log
        self._load_user_activity()
    
    def _load_user_activity(self):
        """Kullanıcı aktivitelerini yükle"""
        if not self.selected_user:
            return
        
        # Basit aktivite bilgisi göster
        user = self.selected_user
        activity_text = f"""
Kullanıcı ID: {user.user_id}
Oluşturulma: {user.created_at}
Son Giriş: {user.last_login or 'Hiç giriş yapılmamış'}
Rol: {user.role}
Depo: {user.warehouse_id}
        """.strip()
        
        self.activity_log.setText(activity_text)
    
    @error_handler_decorator("Kullanıcı kaydedilemedi", show_dialog=True)
    def _save_user(self):
        """Kullanıcıyı kaydet"""
        if not self.selected_user:
            return
        
        # Form verilerini al
        username = self.username_edit.text().strip()
        fullname = self.fullname_edit.text().strip()
        email = self.email_edit.text().strip()
        password = self.password_edit.text().strip()
        role = self.role_combo.currentText()
        warehouse_id = int(self.warehouse_combo.currentText().split(" ")[0])
        is_active = self.active_checkbox.isChecked()
        
        # Validasyon
        if not username or not fullname:
            raise ValidationException("Kullanıcı adı ve tam ad gerekli")
        
        # Update data
        updates = {
            'full_name': fullname,
            'email': email,
            'role': role,
            'warehouse_id': warehouse_id,
            'is_active': is_active
        }
        
        # Şifre değiştirilecekse
        if password:
            updates['password'] = password
        
        # Güncelle
        success = self.session_manager.user_manager.update_user(username, updates)
        
        if success:
            QMessageBox.information(self, "Başarılı", "Kullanıcı başarıyla güncellendi!")
            log_user_action(
                "USER_UPDATE",
                f"User {username} updated",
                target_user=username,
                changes=list(updates.keys())
            )
            self._load_users()
        else:
            QMessageBox.warning(self, "Hata", "Kullanıcı güncellenemedi!")
    
    def _add_new_user(self):
        """Yeni kullanıcı ekleme dialog'u"""
        from .add_user_dialog import AddUserDialog
        
        dialog = AddUserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._load_users()
    
    @error_handler_decorator("Kullanıcı silinemedi", show_dialog=True)
    def _delete_user(self):
        """Kullanıcıyı sil"""
        if not self.selected_user or self.selected_user.username == "admin":
            return
        
        reply = QMessageBox.question(
            self, 
            "Kullanıcı Sil",
            f"'{self.selected_user.full_name}' kullanıcısını silmek istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Basit silme - deaktive et (gerçek silme yerine)
            success = self.session_manager.user_manager.deactivate_user(self.selected_user.username)
            
            if success:
                QMessageBox.information(self, "Başarılı", "Kullanıcı deaktive edildi!")
                log_user_action(
                    "USER_DEACTIVATE",
                    f"User {self.selected_user.username} deactivated",
                    target_user=self.selected_user.username
                )
                self._load_users()
                self.selected_user = None
                self.save_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)
            else:
                QMessageBox.warning(self, "Hata", "Kullanıcı deaktive edilemedi!")