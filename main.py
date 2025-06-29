#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────
#  Uygulama giriş noktası
# ──────────────────────────────────────────────────────────
import os
import logging
import sys
import traceback
from pathlib import Path

# Environment variables'ları ilk önce set et (import'lardan önce!)
os.environ.setdefault("LOGO_SQL_SERVER", "78.135.108.160,1433")
os.environ.setdefault("LOGO_SQL_DB", "logo") 
os.environ.setdefault("LOGO_SQL_USER", "barkod1")
os.environ.setdefault("LOGO_SQL_PASSWORD", "Barkod14*")
os.environ.setdefault("LOGO_COMPANY_NR", "025")
os.environ.setdefault("LOGO_PERIOD_NR", "01")

from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QMessageBox

import app.settings as settings
from app.core.logger import WMSLogger
from app.core.error_handler import setup_global_exception_handler
from app.ui.main_window import MainWindow

# Logger sistemini başlat
WMSLogger.initialize()

# Global exception handler'ı kur
setup_global_exception_handler()

# ──────────────────────────────────────────────────────────
# 1) 4K / yüksek-DPI ekran desteği
# ──────────────────────────────────────────────────────────
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps,   True)

# ──────────────────────────────────────────────────────────
# 2) Ayarları oku  (settings.reload()  → backward compat: load = reload)
# ──────────────────────────────────────────────────────────
CFG = settings.reload()

# ──────────────────────────────────────────────────────────
# 3) QApplication + tema & font
# ──────────────────────────────────────────────────────────
app = QApplication(sys.argv)

# —— Tema ——
theme = CFG["ui"].get("theme", "system")
if theme == "dark":
    app.setStyleSheet("""
        QWidget        { background:#232629; color:#ECECEC; }
        QLineEdit      { background:#2B2E31; border:1px solid #555; }
        QTableWidget::item:selected { background:#3A5FCD; }
    """)
elif theme == "light":
    app.setStyleSheet("")        # Qt’nin varsayılan açık teması
# “system” → işletim sisteminin temasını kullan (hiçbir şey yapma)

# —— Font ——
base_font: QFont = app.font()
base_font.setPointSize(CFG["ui"].get("font_pt", base_font.pointSize()))
app.setFont(base_font)

# ──────────────────────────────────────────────────────────
# 4) Küresel (uncaught) hata yakalayıcı → MessageBox + log
# ──────────────────────────────────────────────────────────
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename = LOG_DIR / "crash.log",
    level    = logging.ERROR,
    format   = "%(asctime)s %(levelname)s: %(message)s"
)

def _excepthook(exctype, value, tb):
    msg = "".join(traceback.format_exception(exctype, value, tb))
    logging.error("UNCAUGHT EXCEPTION:\n%s", msg)
    QMessageBox.critical(None, "Beklenmeyen Hata", msg)
    # sys.__excepthook__ uygulamayı sonlandırır; biz diyalog sonrası devam ediyoruz
sys.excepthook = _excepthook

# ──────────────────────────────────────────────────────────
# 5) Ana pencere
# ──────────────────────────────────────────────────────────
win = MainWindow()
win.show()

# ──────────────────────────────────────────────────────────
# 6) Çıkış
# ──────────────────────────────────────────────────────────
sys.exit(app.exec_())
