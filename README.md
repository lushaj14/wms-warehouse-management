# WMS - Warehouse Management System

Modern depo yönetim sistemi PyQt5 ile geliştirilmiş, barkod tarama, etiket yazdırma ve sevkiyat yönetimi özellikleri içerir.

## 🚀 Özellikler

- **Barkod Tarama**: Ürün barkodlarını okuma ve doğrulama
- **Etiket Yazdırma**: PDF etiket oluşturma ve yazdırma
- **Kullanıcı Yönetimi**: SQL tabanlı kullanıcı sistemi
- **Rol Tabanlı Yetkilendirme**: Admin, Operator, Scanner rolleri
- **Activity Tracking**: Kullanıcı işlemlerini izleme
- **Error Handling**: Merkezi hata yönetimi sistemi
- **Logging**: Gelişmiş loglama ve audit trail

## 🛠️ Kurulum

### Gereksinimler
- Python 3.8+
- SQL Server (opsiyonel)
- PyQt5

### 1. Projeyi İndirin
```bash
git clone https://github.com/lushaj14/wms-warehouse-management.git
cd wms-warehouse-management
```

### 2. Virtual Environment Oluşturun
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. Bağımlılıkları Kurun
```bash
pip install -r requirements.txt
```

### 4. Uygulamayı Çalıştırın
```bash
python main.py
```

## 👤 Kullanıcı Girişi

### Default Admin User
- **Kullanıcı Adı**: `admin`
- **Şifre**: `hakan14` (SQL database varsa)
- **Rol**: Admin (tüm yetkilere sahip)

### User Roles
- **Admin**: Kullanıcı yönetimi + tüm işlemler
- **Operator**: Tarama, yazdırma, sipariş yönetimi
- **Scanner**: Sadece barkod tarama

## 🗄️ Database

### SQL Server (Önerilen)
Uygulama otomatik olarak `WMS_USERS` tablosunu oluşturur.

```sql
-- Environment variables ayarlayın
LOGO_SQL_SERVER=your_server_address
LOGO_SQL_DB=your_database_name
LOGO_SQL_USER=your_username
LOGO_SQL_PASSWORD=your_password
```

### File-based Fallback
SQL Server yoksa otomatik olarak `users.json` dosyası kullanılır.

## 📁 Proje Yapısı

```
wms-warehouse-management/
├── app/
│   ├── core/              # Core systems
│   │   ├── auth.py        # Authentication & session
│   │   ├── user_db.py     # SQL user management
│   │   ├── logger.py      # Advanced logging
│   │   ├── exceptions.py  # Error handling
│   │   └── error_handler.py
│   ├── ui/                # User interface
│   │   ├── pages/         # Application pages
│   │   ├── dialogs/       # Dialog windows
│   │   └── main_window.py
│   ├── dao/               # Database access
│   ├── services/          # Background services
│   └── constants.py       # Application constants
├── tests/                 # Test framework
├── logs/                  # Log files
├── main.py               # Application entry point
└── requirements.txt      # Dependencies
```

## 🧪 Testing

```bash
# Tüm testleri çalıştır
python run_tests.py

# Sadece unit testler
python run_tests.py --type unit

# Coverage ile
python run_tests.py --type all
```

## 📋 Kullanım

### 1. Giriş Yapın
- Uygulamayı başlatın
- Login dialog'unda kullanıcı bilgilerinizi girin

### 2. Barkod Tarama
- Scanner sayfasına gidin
- Sipariş seçin
- Barkodları tarayın

### 3. Etiket Yazdırma
- Tarama tamamlandıktan sonra
- "Etiket Yazdır" butonuna tıklayın

### 4. Kullanıcı Yönetimi (Admin Only)
- Kullanıcı menüsünden "Kullanıcı Yönetimi"
- Yeni kullanıcı ekleyin/düzenleyin

## ⚙️ Konfigürasyon

### Settings
- `config.json`: Genel ayarlar
- `settings.json`: Kullanıcı tercihleri
- Ayarlar sayfasından düzenlenebilir

### Logging
- `logs/wms.log`: Genel application logs
- `logs/errors.log`: Error logs
- Colored console output

## 🔒 Güvenlik

- Password hashing (SHA-256)
- Role-based permissions
- Activity tracking
- Secure database connections

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📝 License

Bu proje MIT lisansı altında lisanslanmıştır.

## 🔧 Troubleshooting

### Database Bağlantı Hatası
```
ValueError: Eksik environment variables: ['LOGO_SQL_SERVER', ...]
```

**Çözüm:**
1. `.env.example` dosyasını `.env` olarak kopyalayın
2. `.env` dosyasındaki database bilgilerini güncelleyin
3. Veya SQL Server yoksa file-based sistemle çalışacak

### PyQt5 Kurulum Sorunu
```bash
pip install PyQt5 --force-reinstall
```

### ODBC Driver Eksik (Windows)
Microsoft ODBC Driver 17+ for SQL Server indirin.

## 🆘 Destek

Sorunlar için [Issues](https://github.com/lushaj14/wms-warehouse-management/issues) bölümünü kullanın.

## 📚 Dokümantasyon

Detaylı bilgi için [CLAUDE.md](CLAUDE.md) dosyasını inceleyin.