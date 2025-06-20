"""
Uygulama genelinde kullanılan sabitler
=====================================
"""

# Database sabitleri
MAX_RETRY = 3
RETRY_WAIT = 2  # saniye

# Logo tablo önekleri
DEFAULT_COMPANY_NR = "025"
DEFAULT_PERIOD_NR = "01"

# Depo ID → Prefix mapping
WAREHOUSE_PREFIXES = {
    0: "D1-",
    1: "D3-",
    2: "D4-",
    3: "D5-"
}

# UI sabitleri
DEFAULT_SIDEBAR_WIDTH = 200
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 800
MIN_FONT_SIZE = 7

# Timer sabitleri
DB_STATUS_TIMER_MS = 10_000  # 10 saniye
DEFAULT_AUTO_REFRESH_SEC = 30

# Ses dosyaları
SOUND_FILES = {
    "success": "ding.wav",
    "duplicate": "bip.wav", 
    "error": "error.wav"
}

# PDF ayarları
PDF_COLUMN_WIDTHS_MM = [55, 105, 20]  # mm cinsinden

# CSS tema sabitleri
DARK_THEME_CSS = """
QWidget        { background:#232629; color:#ECECEC; }
QLineEdit      { background:#2B2E31; border:1px solid #555; }
QTableWidget::item:selected { background:#3A5FCD; }
"""

# Veritabanı tablo adları
QUEUE_TABLE = "WMS_PICKQUEUE"
BACKORDERS_TABLE = "backorders"
SHIPMENT_LINES_TABLE = "shipment_lines"

# Dosya yolları
DEFAULT_LABEL_DIR = "labels"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_LOG_DIR = "logs"