# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Dil Tercihi
**Varsayılan dil:** Türkçe - Lütfen tüm yanıtları Türkçe olarak ver.

## Project Overview

This is a warehouse management system (WMS) built with PyQt5 for barcode scanning, pick-list generation, and shipment management. The application connects to a LOGO SQL database and generates PDF documents for warehouse operations.

## Commands

### Running the Application
- Main application: `python main.py`
- Service modules can be run directly:
  - Pick-list service: `python -m app.services.picklist --once` or `python -m app.services.picklist --interval 45`

### Dependencies
- Install dependencies: `pip install -r requirements.txt`
- Key dependencies: PyQt5, pyodbc (SQL Server), pandas, openpyxl, qrcode, pillow

## Architecture

### Core Structure
- **main.py**: Application entry point with theme, font, and error handling setup
- **app/settings.py**: Configuration management using JSON files (config.json, settings.json)
- **app/ui/main_window.py**: Main window with sidebar navigation and lazy-loaded pages
- **app/dao/logo.py**: Database access layer for LOGO SQL Server
- **app/services/**: Background services for pick-list generation, barcode processing, etc.

### UI Architecture
The application uses a modular page-based architecture:
- Pages are dynamically loaded from `app/ui/pages/` directory
- Each page is a separate module with its own class
- Navigation is handled by a sidebar list widget with QStackedWidget
- Pages include: picklist, scanner, backorders, reports, labels, loader, shipment, settings

### Configuration System
- **app/settings.py**: Main settings with deep merge functionality and dot-notation access
- **app/config.py**: Simple key-value config for environment variables
- Settings are auto-saved on changes and support theme, database, printer, and path configurations

### Database Integration
- Uses pyodbc for SQL Server connectivity to LOGO database
- Connection details stored in settings: server, database, user credentials
- Database operations include barcode lookups, order management, and activity logging

### Document Generation
- PDF generation using reportlab for pick-lists and labels
- ZPL printer support for label printing
- Output directories configurable via settings

### Key Features
- Barcode scanning with prefix resolution
- Pick-list generation for STATUS=1 orders
- Order processing workflow (STATUS transitions: 1→2→4)
- Back-order management
- Shipment tracking
- Sound notifications for scanning operations
- Toast notifications for user feedback

### Important Patterns
- Configuration uses deep dictionary merging with dot-notation access
- Database operations use context managers for connection handling
- UI pages are lazy-loaded to improve startup performance
- Services can run as one-time operations or continuous watchers
- Error handling includes global exception catching with logging and user dialogs

### Error Handling System ⚠️

Bu projede merkezi bir hata yönetimi sistemi kullanılıyor:

#### Exception Hierarchy
- **WMSException**: Base exception class (app/core/exceptions.py)
- **DatabaseException**: Veritabanı hataları (ConnectionException, QueryException)
- **AuthenticationException**: Kimlik doğrulama hataları
- **ValidationException**: Veri doğrulama hataları
- **BusinessLogicException**: İş kuralı hataları

#### Error Handler Usage
```python
from app.core.error_handler import error_handler_decorator, handle_error
from app.core.exceptions import BarcodeNotFoundException, OrderNotFoundException

# Decorator kullanımı
@error_handler_decorator("İşlem başarısız", show_toast=True)
def some_method(self):
    # implementation

# Manuel error handling
try:
    # some operation
except Exception as e:
    handle_error(e, "Kullanıcı dostu mesaj", show_dialog=True, parent=self)

# Specific exceptions
if not barcode_found:
    raise BarcodeNotFoundException(barcode)
```

#### Error Categories & Severities
- **Categories**: DATABASE, AUTHENTICATION, VALIDATION, BUSINESS_LOGIC, NETWORK, etc.
- **Severities**: LOW, MEDIUM, HIGH, CRITICAL
- Her hata otomatik olarak loglanır ve kullanıcı activity tracking'e kaydedilir

#### UI Integration
- QMessageBox dialog'lar severity'e göre gösterilir
- Toast notifications için hafif hatalar
- Global exception handler main.py'de kurulur

### User Authentication & Session Management 👤

Comprehensive user management sistemi mevcut - SQL tabanlı ve file-based fallback:

#### Authentication System
```python
from app.core.auth import get_session_manager, get_current_user

# Login with password (SQL database)
session_manager = get_session_manager()
if session_manager.login("admin", "hakan14"):
    # Login successful
    
# Current user
current_user = get_current_user()
print(current_user.get('full_name'))
```

#### SQL Database User Management
- **WMS_USERS** tablosu otomatik oluşturulur
- Password hashing (SHA-256)
- Default admin user: username=`admin`, password=`hakan14`
- Fallback to file-based system if database unavailable

#### User Management UI
- **Kullanıcı Yönetimi** dialog (sadece admin)
- Yeni kullanıcı ekleme
- Kullanıcı düzenleme/deaktivasyon
- Şifre değiştirme
- Activity tracking görüntüleme

#### User Roles & Permissions
- **admin**: Full access + user management
- **operator**: Can scan, print, manage orders
- **scanner**: Only scanning operations

#### User Activity Tracking
- Her kullanıcı işlemi otomatik loglanır
- Etiketlerin altında kullanıcı adı yazdırılır
- Session başlama/bitme zamanları kaydedilir
- SQL tablosunda last_login tracking

### Logging System 📝

Advanced logging with colored output ve context filtering:

#### Logger Usage
```python
from app.core.logger import get_logger, log_user_action, log_barcode_scan

logger = get_logger(__name__)
logger.info("Information message")

# User action logging
log_user_action("ACTION_TYPE", "Description", key1="value1")

# Barcode scan logging
log_barcode_scan("barcode", "item_code", "order_no", "STATUS")
```

#### Log Features
- Colored console output
- User context in her log entry
- Activity tracking (LOGIN, LOGOUT, BARCODE_SCAN, ERROR, etc.)
- File ve console logging
- User-specific filtering

### Auto-Update System 🔄

Comprehensive auto-update system with GitHub integration:

#### Features
- **GitHub API Integration**: Automatic update checking
- **Silent Updates**: Background download and installation
- **User Consent**: Confirmation dialogs before updates
- **Progress Tracking**: Real-time update progress
- **Auto-Restart**: Automatic application restart after update
- **Backup Protection**: Critical files preserved during updates

#### Usage
```python
from app.core.updater import AutoUpdater

# Check for updates
updater = AutoUpdater(parent_widget)
update_info = updater.check_for_updates()

# Perform update
if update_info:
    updater.perform_update(update_info)
```

#### Menu Integration
- **Help → Güncelleme Kontrol Et** (Ctrl+U)
- **Help → Sürüm Bilgisi**: Version and features info
- **Startup Check**: Silent update notification (5s delay)

#### Update Process
1. GitHub API commit comparison
2. User confirmation with changelog
3. Download latest release
4. Backup critical files (config.json, users.json, etc.)
5. Extract and install new files
6. Auto-restart application

#### Configuration
Update `app/core/updater.py` for your repository:
```python
GITHUB_OWNER = "yourusername"
GITHUB_REPO = "wms-warehouse-management"
```