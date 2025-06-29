"""Scanner Page – Barkod Doğrulama
============================================================
• STATUS = 2 siparişleri listeler (senkron kuyruk: **WMS_PICKQUEUE**)
• Combodan sipariş seçildiğinde otomatik yüklenir; gizli "Yükle" butonu yedekte
• Barkod okutuldukça `qty_sent` DB'de artar → tüm istasyonlar aynı değeri görür
• "Tamamla" → sevkiyat + back‑order + STATUS 4 + kuyruğu temizler
"""
from __future__ import annotations

import getpass
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, List

from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox,
    QInputDialog
)

import app.backorder as bo
import app.settings as st
from app import toast
from app.constants import SOUND_FILES, WAREHOUSE_PREFIXES
from app.core.auth import get_current_user
from app.core.logger import get_logger, log_user_action, log_barcode_scan
from app.core.exceptions import (
    BarcodeNotFoundException, OrderNotFoundException, 
    BusinessLogicException, DatabaseException
)
from app.core.error_handler import error_handler_decorator, handle_error
from app.dao.logo import (
    resolve_barcode_prefix, log_activity, queue_inc, lookup_barcode,
    fetch_picking_orders, fetch_order_lines, update_order_status,
    update_order_header, fetch_order_header, fetch_invoice_no,
    queue_fetch, queue_delete, exec_sql, fetch_one
)
from app.settings import get as cfg
from app.shipment import upsert_header

# ---------------------------------------------------------------------------
# Ses dosyaları
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[3]
SOUND_DIR = BASE_DIR / "sounds"

def _load_wav(name: str) -> QSoundEffect:
    """Ses dosyası yükler"""
    sound = QSoundEffect()
    sound.setSource(QUrl.fromLocalFile(str(SOUND_DIR / name)))
    sound.setVolume(0.9)
    return sound

# Ses efektleri
snd_ok = _load_wav(SOUND_FILES["success"])      # başarılı okuma
snd_dupe = _load_wav(SOUND_FILES["duplicate"])  # yinelenen
snd_err = _load_wav(SOUND_FILES["error"])       # hata

# Label service - opsiyonel
try:
    from app.services.label_service import make_labels as print_labels
except Exception:
    print_labels = None

logger = get_logger(__name__)


def barcode_xref_lookup(barcode: str, warehouse_id: str | None = None):
    """
    Barkodu barcode_xref tablosunda arar, bulamazsa Logo ERP native tablolarında arar.
      • warehouse_id verilmişse → o depoda arar
      • None ise                → depoya bakmadan ilk eşleşmeyi döndürür
    Dönen: (item_code, multiplier)  |  (None, None)
    """
    try:
        # İlk önce custom barcode_xref tablosuna bak
        if warehouse_id is not None:
            row = fetch_one(
                "SELECT TOP 1 item_code, multiplier "
                "FROM barcode_xref WHERE barcode=? AND warehouse_id=?",
                barcode, warehouse_id
            )
        else:
            row = fetch_one(
                "SELECT TOP 1 item_code, multiplier "
                "FROM barcode_xref WHERE barcode=?", barcode
            )
        if row:
            return row["item_code"], row.get("multiplier", 1)
        
        # Bulamazsa Logo ERP native tablolarında ara
        from app.dao.logo import resolve_barcode_prefix
        if warehouse_id is not None:
            try:
                wh_id = int(warehouse_id) if isinstance(warehouse_id, str) else warehouse_id
                item_code = resolve_barcode_prefix(barcode, wh_id)
                if item_code:
                    logger.info(f"Barkod Logo ERP'de bulundu: {barcode} -> {item_code}")
                    return item_code, 1  # default multiplier
            except (ValueError, TypeError):
                pass
        
    except Exception as exc:
        logger.error(f"[barcode_xref_lookup] DB error: {exc}")
    return None, None


class ScannerPage(QWidget):
    """Barkod tarama sayfası"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self._current_order = None  # order_no (string)
        self._current_order_id = None  # order_id (int) 
        self._order_lines = []
        self._setup_ui()
        self._load_orders()
        
        # Auto-refresh timer for picking orders (30 seconds)
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._load_orders)
        self._refresh_timer.start(30000)  # 30 saniye

    def _setup_ui(self):
        """UI bileşenlerini oluşturur"""
        layout = QVBoxLayout(self)
        
        # Sipariş seçimi
        self._setup_order_selection(layout)
        
        # Barkod girişi
        self._setup_barcode_input(layout)
        
        # Ürün tablosu
        self._setup_product_table(layout)
        
        # Kontrol butonları
        self._setup_control_buttons(layout)

    def _setup_order_selection(self, layout):
        """Sipariş seçim bölümü"""
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("Sipariş:"))
        
        self.order_combo = QComboBox()
        self.order_combo.currentTextChanged.connect(self._order_selected)
        order_layout.addWidget(self.order_combo)
        
        self.reload_btn = QPushButton("Yenile")
        self.reload_btn.clicked.connect(self._load_orders)
        order_layout.addWidget(self.reload_btn)
        
        layout.addLayout(order_layout)

    def _setup_barcode_input(self, layout):
        """Barkod giriş bölümü"""
        barcode_layout = QHBoxLayout()
        barcode_layout.addWidget(QLabel("Barkod:"))
        
        self.barcode_input = QLineEdit()
        self.barcode_input.returnPressed.connect(self._process_barcode)
        barcode_layout.addWidget(self.barcode_input)
        
        layout.addLayout(barcode_layout)

    def _setup_product_table(self, layout):
        """Ürün tablosu"""
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Ürün Kodu", "İstenen", "Taranan", "Kalan"])
        
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        
        layout.addWidget(self.table)

    def _setup_control_buttons(self, layout):
        """Kontrol butonları"""
        button_layout = QHBoxLayout()
        
        self.complete_btn = QPushButton("Tamamla")
        self.complete_btn.clicked.connect(self._complete_order)
        self.complete_btn.setEnabled(False)
        
        self.print_btn = QPushButton("Etiket Yazdır")
        self.print_btn.clicked.connect(self._print_labels)
        self.print_btn.setEnabled(False)
        
        button_layout.addWidget(self.complete_btn)
        button_layout.addWidget(self.print_btn)
        layout.addLayout(button_layout)

    @error_handler_decorator("Siparişler yüklenemedi", show_toast=True)
    def _load_orders(self, checked=None):
        """Siparişleri yükle"""
        orders = fetch_picking_orders()
        self.logger.info(f"Scanner'a {len(orders)} picking siparişi yüklendi")
        self.order_combo.clear()
        self.order_combo.addItem("-- Sipariş Seçin --")
        
        for order in orders:
            display_text = f"{order['order_no']} ({order['customer_name']})"
            self.order_combo.addItem(display_text, order['order_id'])  # order_id'yi data olarak sakla

    def _order_selected(self, order_text: str):
        """Sipariş seçildiğinde çalışır"""
        if order_text.startswith("--"):
            self._current_order = None
            self._current_order_id = None
            self._order_lines = []
            self.table.setRowCount(0)
            self.complete_btn.setEnabled(False)
            self.print_btn.setEnabled(False)
            return
        
        # Seçili item'dan order_id'yi al
        current_index = self.order_combo.currentIndex()
        if current_index > 0:  # İlk item "-- Sipariş Seçin --" olduğu için
            order_id = self.order_combo.itemData(current_index)
            order_no = order_text.split(" ")[0]
            self._current_order = order_no
            self._current_order_id = order_id  # ID'yi de sakla
            self._load_order_lines(order_id)

    @error_handler_decorator("Sipariş satırları yüklenemedi", show_dialog=True)
    def _load_order_lines(self, order_id: int):
        """Sipariş satırlarını yükle ve WMS queue state ile senkronize et"""
        from app.dao.logo import queue_fetch
        
        # Logo ERP'den order lines'ı al
        self._order_lines = fetch_order_lines(order_id)
        if not self._order_lines:
            raise OrderNotFoundException(f"Order ID: {order_id}")
        
        # WMS queue state ile senkronize et
        try:
            queue_lines = queue_fetch(order_id)
            for line in self._order_lines:
                # Queue'dan qty_sent değerini al
                queue_line = next((q for q in queue_lines if q["item_code"] == line["item_code"]), None)
                if queue_line:
                    line["qty_scanned"] = queue_line["qty_sent"]
                    self.logger.debug(f"Synced {line['item_code']}: scanned={queue_line['qty_sent']}")
                else:
                    line["qty_scanned"] = 0
        except Exception as e:
            self.logger.warning(f"Queue sync failed: {e}, using defaults")
            for line in self._order_lines:
                line["qty_scanned"] = 0
        
        self._update_table()
        self.complete_btn.setEnabled(True)
        self.print_btn.setEnabled(True)

    def _update_table(self):
        """Tabloyu güncelle"""
        self.table.setRowCount(len(self._order_lines))
        
        for i, line in enumerate(self._order_lines):
            self.table.setItem(i, 0, QTableWidgetItem(line["item_code"]))
            self.table.setItem(i, 1, QTableWidgetItem(str(line["qty_ordered"])))
            self.table.setItem(i, 2, QTableWidgetItem(str(line.get("qty_scanned", 0))))
            
            remaining = line["qty_ordered"] - line.get("qty_scanned", 0)
            self.table.setItem(i, 3, QTableWidgetItem(str(remaining)))

    @error_handler_decorator("Barkod işlenemedi", show_toast=True)
    def _process_barcode(self):
        """Barkod işle"""
        barcode = self.barcode_input.text().strip()
        if not barcode or not self._current_order:
            return
        
        try:
            # Warehouse ID'yi order lines'dan al (fallback için gerekli)
            warehouse_id = None
            if self._order_lines:
                warehouse_id = self._order_lines[0].get("warehouse_id", 0)
            
            # Barkod lookup (fallback mechanism ile)
            item_code, multiplier = barcode_xref_lookup(barcode, warehouse_id)
            
            if not item_code:
                snd_err.play()
                raise BarcodeNotFoundException(barcode)
            
            # Siparişte var mı kontrol et
            line = next((l for l in self._order_lines if l["item_code"] == item_code), None)
            if not line:
                snd_err.play()
                raise BusinessLogicException(
                    f"Ürün kodu {item_code} bu siparişte bulunmuyor",
                    context={"barcode": barcode, "item_code": item_code, "order_no": self._current_order}
                )
            
            # Miktar kontrolü
            scanned = line.get("qty_scanned", 0)
            if scanned >= line["qty_ordered"]:
                snd_dupe.play()
                raise BusinessLogicException(
                    f"Ürün {item_code} zaten tamamlandı",
                    context={"item_code": item_code, "qty_scanned": scanned, "qty_ordered": line["qty_ordered"]}
                )
            
            # Miktarı artır (order_id kullan, order_no değil!)
            queue_inc(self._current_order_id, item_code, multiplier or 1)
            line["qty_scanned"] = scanned + (multiplier or 1)
            
            # Tabloyu güncelle
            self._update_table()
            snd_ok.play()
            
            # Activity log - yeni sistem
            current_user = get_current_user()
            log_barcode_scan(barcode, item_code, self._current_order, "SUCCESS")
            log_user_action(
                "BARCODE_SCAN",
                f"Barkod başarıyla tarandı",
                barcode=barcode,
                item_code=item_code,
                order_no=self._current_order,
                qty_scanned=multiplier or 1,
                warehouse_id=line.get("warehouse_id", 0)
            )
            
            # Eski sistem (backward compatibility)
            log_activity(
                current_user.get('username', 'unknown') if current_user else 'anonymous',
                "SCAN",
                f"Barkod tarandı: {barcode}",
                order_no=self._current_order,
                item_code=item_code,
                qty_scanned=multiplier or 1
            )
            
        except (BarcodeNotFoundException, BusinessLogicException):
            # Bu hataları yeniden fırlat - UI'da handle edilecek
            raise
        except Exception as exc:
            # Beklenmeyen hatalar için generic error
            snd_err.play()
            handle_error(exc, "Barkod işlenirken beklenmeyen hata", show_toast=True, parent=self)
        
        finally:
            self.barcode_input.clear()

    @error_handler_decorator("Sipariş tamamlanamadı", show_dialog=True)
    def _complete_order(self, checked=None):
        """Siparişi tamamla"""
        if not self._current_order:
            return
        
        # Eksik kontrol
        incomplete_items = [
            line for line in self._order_lines
            if line.get("qty_scanned", 0) < line["qty_ordered"]
        ]
        
        if incomplete_items:
            reply = QMessageBox.question(
                self, "Eksik Ürünler",
                f"{len(incomplete_items)} ürün eksik! Yine de tamamlansın mı?"
            )
            if reply != QMessageBox.Yes:
                return
        
        # Siparişi tamamla (order_id kullan!)
        update_order_status(self._current_order_id, 4)  # STATUS = 4 (Tamamlandı)
        
        # Sevkiyat kayıtları
        for line in self._order_lines:
            scanned = line.get("qty_scanned", 0)
            if scanned > 0:
                # Shipment record
                bo.add_shipment(
                    self._current_order,
                    str(date.today()),
                    line["item_code"],
                    line.get("warehouse_id", 0),
                    line["qty_ordered"],
                    scanned
                )
        
        # Kuyruktan temizle (order_id kullan!)
        queue_delete(self._current_order_id)
        
        from app import toast
        toast("Başarılı", "Sipariş tamamlandı!")
        self._load_orders()  # Listeyi yenile

    @error_handler_decorator("Etiketler yazdırılamadı", show_dialog=True)
    def _print_labels(self, checked=None):
        """Etiketleri yazdır"""
        if not print_labels or not self._current_order:
            QMessageBox.information(self, "Bilgi", "Etiket servisi mevcut değil!")
            return
        
        scanned_items = [
            line for line in self._order_lines
            if line.get("qty_scanned", 0) > 0
        ]
        
        if not scanned_items:
            QMessageBox.information(self, "Bilgi", "Yazdırılacak ürün yok!")
            return
        
        # Etiket yazdırma servisi çağır
        print_labels(self._current_order, scanned_items)
        toast.show("Başarılı", "Etiketler yazdırıldı!")

    def apply_settings(self):
        """Ayarlar değiştiğinde çağrılır"""
        # Ses seviyesi güncellemesi
        volume = st.get("ui.sounds.volume", 0.9)
        enabled = st.get("ui.sounds.enabled", True)
        
        if enabled:
            snd_ok.setVolume(volume)
            snd_dupe.setVolume(volume)
            snd_err.setVolume(volume)
        else:
            snd_ok.setVolume(0)
            snd_dupe.setVolume(0)
            snd_err.setVolume(0)