"""MainWindow – modüler PyQt5 çerçevesi
================================================
Bu dosya yalnızca **sidebar + lazy‑load QStackedWidget** barındırır.
Her sekme kendi modülünde:

    app/ui/pages/picklist_page.py
    app/ui/pages/scanner_page.py
    ...

Yeni sekme eklemek = sadece module + class adı listesine eklemek.
"""
from importlib import import_module
from pathlib import Path
from typing import Dict

from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QListWidgetItem, QStackedWidget,
    QHBoxLayout, QSizePolicy, QAction, QLabel, QDialog, QVBoxLayout,
    QTextEdit, QApplication
)

from app import register_toast
from app.core.auth import get_session_manager, get_current_user
from app.core.logger import get_logger, log_user_action
from app.ui.toast import Toast
from app.ui.dialogs.activity_viewer import ActivityViewer
from app.ui.dialogs.login_dialog import LoginDialog, UserSwitchDialog

# ---------------------------------------------------------------------------
# Sidebar tanımı
# ---------------------------------------------------------------------------
_PAGES = [
    ("Pick-List", "document-print", "picklist_page", "PicklistPage"),
    ("Scanner", "system-search", "scanner_page", "ScannerPage"),
    ("Back-Orders", "view-list", "backorders_page", "BackordersPage"),
    ("Rapor", "x-office-spreadsheet", "report_page", "ReportPage"),
    ("Etiket", "emblem-ok", "label_page", "LabelPage"),
    ("Loader", "folder-download", "loader_page", "LoaderPage"),
    ("Sevkiyat", "truck", "shipment_page", "ShipmentPage"),
    ("Ayarlar", "preferences-system", "settings_page", "SettingsPage"),
    ("Görevler", "view-task", "taskboard_page", "TaskBoardPage"),
    ("Kullanıcılar", "user-group", "user_page", "UserPage"),
    ("Yardım", "help-about", "help_page", "HelpPage"),
    ("Barkodlar", "qrcode", "barcode_page", "BarcodePage"),
]

BASE_DIR = Path(__file__).resolve().parent

# Koyu tema stylesheet'i
DARK_CSS = """
QWidget        { background:#232629; color:#ECECEC; }
QLineEdit      { background:#2B2E31; border:1px solid #555; }
QTableWidget::item:selected { background:#3A5FCD; }
"""


class HelpDialog(QDialog):
    """Klavye kısayolları yardım penceresi"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kısayol Kılavuzu")
        self.resize(400, 270)
        
        text_edit = QTextEdit(readOnly=True)
        text_edit.setHtml("""
        <h3>Klavye Kısayolları</h3>
        <ul>
          <li><b>Ctrl + + / Ctrl + -</b> – Yazı boyutu büyüt/küçült</li>
          <li><b>Ctrl + D</b> – Koyu Tema Aç/Kapat</li>
          <li><b>F5</b> – Listeyi yenile (Loader)</li>
          <li><b>F1</b> – Bu pencere</li>
        </ul>
        """)
        
        layout = QVBoxLayout(self)
        layout.addWidget(text_edit)


class MainWindow(QMainWindow):
    """Ana uygulama penceresi"""
    
    def __init__(self):
        super().__init__()
        
        # Logger'ı başlat
        self.logger = get_logger(__name__)
        self.session_manager = get_session_manager()
        
        # Toast sistemi
        register_toast(self._show_toast)
        
        # Login kontrolü
        if not self._handle_login():
            self.close()
            return
        
        # Ana pencere ayarları
        self.setWindowTitle("LOGLine Yönetim Paneli (Modüler)")
        self.resize(1280, 800)
        self._pages: Dict[str, QWidget] = {}
        self._db_err_warned = False
        
        # UI'ı başlat
        self._init_ui()
        
        # User activity log
        log_user_action("MAIN_WINDOW_OPENED", "Ana pencere açıldı")

    def _handle_login(self) -> bool:
        """Login işlemini yönet"""
        login_dialog = LoginDialog(self)
        login_dialog.login_successful.connect(self._on_login_success)
        
        if login_dialog.exec_() == QDialog.Accepted:
            return True
        return False
    
    def _on_login_success(self, user_dict):
        """Login başarılı olduğunda çağrılır"""
        user = self.session_manager.get_current_user()
        self.logger.info(f"User logged in: {user.username}")
        
        # Window title'a kullanıcı adını ekle
        self.setWindowTitle(f"LOGLine Yönetim Paneli - {user.full_name} ({user.role})")
    
    def _show_toast(self, title: str, msg: str | None = None):
        """Toast callback fonksiyonu"""
        Toast(title, msg, parent=self).popup()

    def _init_ui(self):
        """Ana UI'ı başlatır"""
        self._setup_central_widget()
        self._setup_sidebar()
        self._setup_content_area()
        self._setup_menu_bar()
        self._setup_status_bar()
        self._setup_db_timer()
        self._setup_auto_updater()

    def _setup_central_widget(self):
        """Merkezi widget'ı oluşturur"""
        central = QWidget()
        self.setCentralWidget(central)
        self.layout = QHBoxLayout(central)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def _setup_sidebar(self):
        """Sidebar'ı oluşturur"""
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        
        # Sidebar renk ayarları
        palette = QPalette()
        palette.setColor(QPalette.Base, QColor("#2C3E50"))
        palette.setColor(QPalette.Text, QColor("#ECF0F1"))
        self.sidebar.setPalette(palette)
        
        # Sidebar öğelerini ekle
        for title, icon, *_ in _PAGES:
            item = QListWidgetItem(QIcon.fromTheme(icon), title)
            item.setSizeHint(QSize(180, 40))
            self.sidebar.addItem(item)
        
        self.sidebar.currentRowChanged.connect(self._change_page)
        self.layout.addWidget(self.sidebar)

    def _setup_content_area(self):
        """İçerik alanını oluşturur"""
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.stack)
        
        # İlk sayfa
        self.sidebar.setCurrentRow(0)

    def _setup_menu_bar(self):
        """Menü çubuğunu oluşturur"""
        menu_bar = self.menuBar()
        
        # Kullanıcı menüsü
        user_menu = menu_bar.addMenu("Kullanıcı")
        
        # Mevcut kullanıcı bilgisi
        current_user = self.session_manager.get_current_user()
        user_info_action = QAction(f"👤 {current_user.full_name} ({current_user.role})", self)
        user_info_action.setEnabled(False)
        user_menu.addAction(user_info_action)
        user_menu.addSeparator()
        
        # Kullanıcı yönetimi (sadece admin için)
        if current_user.role == "admin":
            user_mgmt_action = QAction("Kullanıcı Yönetimi", self)
            user_mgmt_action.triggered.connect(self._open_user_management)
            user_menu.addAction(user_mgmt_action)
            user_menu.addSeparator()
        
        # Kullanıcı değiştir
        switch_user_action = QAction("Kullanıcı Değiştir", self)
        switch_user_action.triggered.connect(self._switch_user)
        user_menu.addAction(switch_user_action)
        
        # Çıkış yap
        logout_action = QAction("Çıkış Yap", self, shortcut="Ctrl+Q")
        logout_action.triggered.connect(self._logout)
        user_menu.addAction(logout_action)
        
        # Günlükler menüsü
        log_menu = menu_bar.addMenu("Günlükler")
        act_logs = QAction("Kullanıcı Aktiviteleri", self)
        act_logs.triggered.connect(self._open_activity_viewer)
        log_menu.addAction(act_logs)
        
        # Görünüm menüsü
        view_menu = menu_bar.addMenu("Görünüm")
        self.act_dark = QAction("Koyu Tema", self, checkable=True, shortcut="Ctrl+D")
        self.act_dark.triggered.connect(self.toggle_dark)
        view_menu.addAction(self.act_dark)
        
        self.act_font_inc = QAction("Yazı +1", self, shortcut="Ctrl++")
        self.act_font_dec = QAction("Yazı -1", self, shortcut="Ctrl+-")
        self.act_font_inc.triggered.connect(lambda: self.bump_font(+1))
        self.act_font_dec.triggered.connect(lambda: self.bump_font(-1))
        view_menu.addAction(self.act_font_inc)
        view_menu.addAction(self.act_font_dec)
        
        # Yardım menüsü
        help_menu = menu_bar.addMenu("Yardım")
        
        # Güncelleme kontrol et
        update_action = QAction("Güncelleme Kontrol Et", self, shortcut="Ctrl+U")
        update_action.triggered.connect(self._check_for_updates)
        help_menu.addAction(update_action)
        
        help_menu.addSeparator()
        
        # Version bilgisi
        version_action = QAction("Sürüm Bilgisi", self)
        version_action.triggered.connect(self._show_version_info)
        help_menu.addAction(version_action)
        
        # Kısayol kılavuzu
        act_help = QAction("Kısayol Kılavuzu", self, shortcut="F1")
        act_help.triggered.connect(lambda: HelpDialog(self).exec_())
        help_menu.addAction(act_help)

    def _setup_status_bar(self):
        """Durum çubuğunu oluşturur"""
        # Kullanıcı bilgisi
        current_user = self.session_manager.get_current_user()
        self.lbl_user = QLabel(f"👤 {current_user.username} | {current_user.role}")
        self.lbl_user.setStyleSheet("color: #2c3e50; font-weight: bold; padding: 2px 8px;")
        self.statusBar().addWidget(self.lbl_user)
        
        # Spacer
        self.statusBar().addWidget(QLabel(""), 1)
        
        # DB connection status
        self.lbl_db = QLabel("●")
        self.lbl_db.setStyleSheet("color:grey")
        self.statusBar().addPermanentWidget(self.lbl_db)

    def _setup_db_timer(self):
        """Veritabanı durumu timer'ını başlatır"""
        self._db_timer = QTimer(self)
        self._db_timer.timeout.connect(self._update_db_status)
        self._db_timer.start(10_000)  # 10 saniye
        self._update_db_status()

    def _open_activity_viewer(self):
        """Aktivite görüntüleyici penceresini açar"""
        log_user_action("ACTIVITY_VIEWER_OPENED", "Aktivite görüntüleyici açıldı")
        ActivityViewer(self).exec_()
    
    def _switch_user(self):
        """Kullanıcı değiştir"""
        current_user = self.session_manager.get_current_user()
        switch_dialog = UserSwitchDialog(current_user, self)
        
        if switch_dialog.exec_() == QDialog.Accepted:
            # UI'ı güncelle
            new_user = self.session_manager.get_current_user()
            self.setWindowTitle(f"LOGLine Yönetim Paneli - {new_user.full_name} ({new_user.role})")
            self.lbl_user.setText(f"👤 {new_user.username} | {new_user.role}")
            
            # Menü'yü yeniden oluştur
            self.menuBar().clear()
            self._setup_menu_bar()
            
            self._show_toast("Kullanıcı Değişti", f"Şimdi {new_user.full_name} olarak giriş yaptınız")
    
    def _logout(self):
        """Çıkış yap"""
        from PyQt5.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, 
            "Çıkış Yap", 
            "Uygulamadan çıkmak istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            log_user_action("LOGOUT", "Kullanıcı çıkış yaptı")
            self.session_manager.logout()
            self.close()

    def _load_page(self, idx: int):
        """
        Sayfa yükleme fonksiyonu
        • İlk tıklamada sayfanın modülünü import eder, widget'ı yaratır.
        • Tekrar tıklamalarda önceden üretilen widget önbellekten alınır.
        """
        title, _icon, mod_name, cls_name = _PAGES[idx]

        # Önbellekten kontrol et
        if title in self._pages:
            return self._pages[title]

        try:
            mod = import_module(f"app.ui.pages.{mod_name}")
            widget = getattr(mod, cls_name)()
        except Exception as exc:
            # Hata durumunda placeholder
            widget = QLabel(f"<b>{title}</b><br>Yükleme hatası:<br>{exc}")
            widget.setAlignment(Qt.AlignCenter)

        # Apply settings varsa uygula
        if hasattr(widget, "apply_settings") and callable(widget.apply_settings):
            widget.apply_settings()

        # Ayarlar paneli ise kaydet sinyalini yakala
        if title == "Ayarlar" and hasattr(widget, "settings_saved"):
            widget.settings_saved.connect(self._apply_global_settings)

        self.stack.addWidget(widget)
        self._pages[title] = widget
        return widget

    def _apply_global_settings(self):
        """Ayarlar değiştiğinde global ayarları uygular"""
        import app.settings as st

        # Tema ayarları
        theme = st.get("ui.theme", "system")
        if theme == "dark":
            QApplication.instance().setStyleSheet(DARK_CSS)
        elif theme == "light":
            QApplication.instance().setStyleSheet("")

        # Font ayarları
        base_font = QApplication.instance().font()
        base_font.setPointSize(st.get("ui.font_pt", base_font.pointSize()))
        QApplication.instance().setFont(base_font)

        # Toast süresi
        from app.ui import toast
        toast.DEFAULT_SECS = st.get("ui.toast_secs", 3)

        # Ses ayarları
        try:
            from app.sound import set_global_volume
            set_global_volume(
                st.get("ui.sounds.volume", 0.9),
                enabled=st.get("ui.sounds.enabled", True)
            )
        except ImportError:
            pass

        # Açık sayfalara ayarları ilet
        for widget in self._pages.values():
            if hasattr(widget, "apply_settings") and callable(widget.apply_settings):
                widget.apply_settings()

    def _change_page(self, idx: int):
        """Sidebar'da seçilen sayfayı gösterir"""
        self.stack.setCurrentWidget(self._load_page(idx))

    def toggle_dark(self, checked: bool):
        """Koyu tema toggle"""
        if checked:
            self.setStyleSheet(DARK_CSS)
        else:
            self.setStyleSheet("")

    def bump_font(self, delta: int = 1):
        """Yazı boyutu değiştir"""
        font = self.font()
        font.setPointSize(max(7, font.pointSize() + delta))
        self.setFont(font)
        self.sidebar.setFont(font)
        self.stack.setFont(font)

    def _open_user_management(self):
        """Kullanıcı yönetimi dialog'unu aç"""
        from app.ui.dialogs.user_management_dialog import UserManagementDialog
        
        dialog = UserManagementDialog(self)
        dialog.exec_()

    def _setup_auto_updater(self):
        """Auto-updater'ı başlat"""
        try:
            from app.core.updater import AutoUpdater
            self.auto_updater = AutoUpdater(self)
            
            # Startup'ta güncelleme kontrol et (5 saniye sonra)
            QTimer.singleShot(5000, self.auto_updater.check_updates_on_startup)
            
        except ImportError as e:
            self.logger.warning(f"Auto-updater not available: {e}")
    
    def _check_for_updates(self):
        """Güncelleme kontrol et"""
        try:
            if hasattr(self, 'auto_updater'):
                update_info = self.auto_updater.check_for_updates()
                if update_info:
                    self.auto_updater.perform_update(update_info)
            else:
                QMessageBox.information(
                    self,
                    "Güncelleme",
                    "Otomatik güncelleme sistemi mevcut değil.\n"
                    "GitHub'dan manuel olarak indirebilirsiniz."
                )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Güncelleme Hatası", 
                f"Güncelleme kontrolünde hata: {str(e)}"
            )
    
    def _show_version_info(self):
        """Version bilgisi göster"""
        try:
            import json
            from pathlib import Path
            
            version_file = Path(__file__).parent.parent.parent / "version.json"
            if version_file.exists():
                with open(version_file, 'r', encoding='utf-8') as f:
                    version_data = json.load(f)
                
                features_text = "\n".join(f"• {feature}" for feature in version_data.get('features', []))
                
                version_text = f"""
<h3>WMS - Warehouse Management System</h3>
<p><b>Sürüm:</b> {version_data.get('version', 'Bilinmiyor')}</p>
<p><b>Build Tarihi:</b> {version_data.get('build_date', 'Bilinmiyor')}</p>
<p><b>Son Güncelleme:</b> {version_data.get('updated_at', 'Bilinmiyor')}</p>
<p><b>Güncelleme Yöntemi:</b> {version_data.get('update_method', 'Bilinmiyor')}</p>

<h4>Özellikler:</h4>
<p>{features_text}</p>

<hr>
<p><small>Geliştirici: Can Otomotiv IT Ekibi<br>
GitHub: github.com/yourusername/wms-warehouse-management</small></p>
                """.strip()
                
                QMessageBox.about(self, "Sürüm Bilgisi", version_text)
            else:
                QMessageBox.information(
                    self,
                    "Sürüm Bilgisi",
                    "Version bilgisi bulunamadı."
                )
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Hata",
                f"Version bilgisi okunamadı: {str(e)}"
            )

    def _update_db_status(self):
        """Veritabanı bağlantı durumunu kontrol et"""
        from app.dao.logo import fetch_one
        try:
            fetch_one("SELECT 1")
            self.lbl_db.setStyleSheet("color:lime")
            self._db_err_warned = False
        except Exception as exc:
            self.lbl_db.setStyleSheet("color:red")
            if not self._db_err_warned:
                self._show_toast("DB Bağlantı Hatası", str(exc)[:120])
                self._db_err_warned = True


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())