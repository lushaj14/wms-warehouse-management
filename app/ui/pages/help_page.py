"""
Yardım Sayfası
==============
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QTabWidget, QScrollArea
)

from app.core.logger import get_logger, log_user_action


class HelpPage(QWidget):
    """Yardım ve dokümantasyon sayfası"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self._setup_ui()
    
    def _setup_ui(self):
        """UI bileşenlerini oluştur"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Yardım ve Dokümantasyon")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Tab widget
        tab_widget = QTabWidget()
        
        # Klavye kısayolları tab
        shortcuts_tab = self._create_shortcuts_tab()
        tab_widget.addTab(shortcuts_tab, "Klavye Kısayolları")
        
        # Kullanım kılavuzu tab
        guide_tab = self._create_guide_tab()
        tab_widget.addTab(guide_tab, "Kullanım Kılavuzu")
        
        # Hakkında tab
        about_tab = self._create_about_tab()
        tab_widget.addTab(about_tab, "Hakkında")
        
        layout.addWidget(tab_widget)
        
        # Yardım logla
        log_user_action("HELP_PAGE_OPENED", "Yardım sayfası açıldı")
    
    def _create_shortcuts_tab(self):
        """Klavye kısayolları tab'ını oluştur"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        shortcuts_text.setHtml("""
        <h3>Klavye Kısayolları</h3>
        
        <h4>Genel Kısayollar</h4>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 8px; border: 1px solid #ddd;"><b>Kısayol</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;"><b>Açıklama</b></td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">Ctrl + Q</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Çıkış Yap</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 8px; border: 1px solid #ddd;">Ctrl + D</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Koyu Tema Aç/Kapat</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">Ctrl + +</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Yazı Boyutunu Büyüt</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 8px; border: 1px solid #ddd;">Ctrl + -</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Yazı Boyutunu Küçült</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">Ctrl + U</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Güncelleme Kontrol Et</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td style="padding: 8px; border: 1px solid #ddd;">F1</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Kısayol Kılavuzu</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">F5</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Listeyi Yenile (Loader)</td>
            </tr>
        </table>
        
        <h4>Tarama Sayfası</h4>
        <ul>
            <li><b>Enter:</b> Barkod tarama işlemini tamamla</li>
            <li><b>Tab:</b> Sonraki alana geç</li>
            <li><b>Esc:</b> Mevcut işlemi iptal et</li>
        </ul>
        """)
        
        layout.addWidget(shortcuts_text)
        return widget
    
    def _create_guide_tab(self):
        """Kullanım kılavuzu tab'ını oluştur"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setHtml("""
        <h3>Depo Yönetim Sistemi Kullanım Kılavuzu</h3>
        
        <h4>1. Giriş Yapma</h4>
        <p>Uygulama açıldığında giriş ekranı görünür. Kullanıcı adınızı seçin ve şifrenizi girin.</p>
        <ul>
            <li><b>Admin:</b> Tüm özelliklere erişim</li>
            <li><b>Operator:</b> Tarama, yazdırma ve sipariş yönetimi</li>
            <li><b>Scanner:</b> Sadece barkod tarama</li>
        </ul>
        
        <h4>2. Pick-List İşlemleri</h4>
        <p>Pick-List sayfasında sipariş listelerini görüntüleyebilir ve yazdırabilirsiniz.</p>
        <ul>
            <li>Siparişleri listeleyin</li>
            <li>Detayları görüntüleyin</li>
            <li>Pick-list yazdırın</li>
        </ul>
        
        <h4>3. Barkod Tarama</h4>
        <p>Scanner sayfasında barkod okutma işlemlerini gerçekleştirin.</p>
        <ul>
            <li>Sipariş numarasını girin</li>
            <li>Ürün barkodunu okutun</li>
            <li>Miktarları kontrol edin</li>
            <li>İşlemi tamamlayın</li>
        </ul>
        
        <h4>4. Etiket Yazdırma</h4>
        <p>Etiket sayfasında ürün etiketlerini oluşturun ve yazdırın.</p>
        <ul>
            <li>Ürün bilgilerini girin</li>
            <li>QR kod oluşturun</li>
            <li>Etiketi yazdırın</li>
        </ul>
        
        <h4>5. Raporlar</h4>
        <p>Rapor sayfasında çeşitli raporlara erişin.</p>
        <ul>
            <li>Günlük aktivite raporları</li>
            <li>Tarama istatistikleri</li>
            <li>Hata raporları</li>
        </ul>
        
        <h4>6. Ayarlar</h4>
        <p>Ayarlar sayfasında sistem tercihlerinizi yapılandırın.</p>
        <ul>
            <li>Tema ayarları</li>
            <li>Yazı boyutu</li>
            <li>Ses ayarları</li>
            <li>Veritabanı bağlantısı</li>
        </ul>
        """)
        
        layout.addWidget(guide_text)
        return widget
    
    def _create_about_tab(self):
        """Hakkında tab'ını oluştur"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <div style="text-align: center;">
            <h2>WMS - Warehouse Management System</h2>
            <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==" 
                 width="100" height="100" style="background-color: #3498db; border-radius: 50px;">
        </div>
        
        <h3>Proje Bilgileri</h3>
        <ul>
            <li><b>Adı:</b> WMS - Depo Yönetim Sistemi</li>
            <li><b>Sürüm:</b> 1.0.0</li>
            <li><b>Geliştirici:</b> Can Otomotiv IT Ekibi</li>
            <li><b>Framework:</b> PyQt5</li>
            <li><b>Veritabanı:</b> SQL Server / Dosya Tabanlı</li>
        </ul>
        
        <h3>Özellikler</h3>
        <ul>
            <li>✅ Kullanıcı yönetimi ve rol tabanlı erişim</li>
            <li>✅ Barkod tarama ve doğrulama</li>
            <li>✅ Pick-list yönetimi</li>
            <li>✅ Etiket yazdırma</li>
            <li>✅ QR kod oluşturma</li>
            <li>✅ Aktivite loglama</li>
            <li>✅ Hata yönetimi</li>
            <li>✅ Otomatik güncelleme</li>
            <li>✅ Koyu/açık tema desteği</li>
            <li>✅ Çoklu dil desteği (TR/EN)</li>
        </ul>
        
        <h3>Teknical Stack</h3>
        <ul>
            <li><b>Python:</b> 3.8+</li>
            <li><b>GUI Framework:</b> PyQt5</li>
            <li><b>Database:</b> SQL Server (pyodbc)</li>
            <li><b>QR/Barcode:</b> qrcode, python-barcode</li>
            <li><b>Logging:</b> Python logging module</li>
        </ul>
        
        <h3>Lisans</h3>
        <p>Bu yazılım Can Otomotiv şirketi için geliştirilmiştir. Tüm hakları saklıdır.</p>
        
        <h3>Destek</h3>
        <p>Teknik destek için IT ekibi ile iletişime geçin.</p>
        <ul>
            <li><b>E-posta:</b> it@canotomotiv.com</li>
            <li><b>GitHub:</b> github.com/yourusername/wms-warehouse-management</li>
        </ul>
        
        <hr>
        <p style="text-align: center; color: #666; font-size: 10px;">
            Copyright © 2024 Can Otomotiv. All rights reserved.
        </p>
        """)
        
        layout.addWidget(about_text)
        return widget
    
    def apply_settings(self):
        """Ayarları uygula (main_window tarafından çağrılır)"""
        pass