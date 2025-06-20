"""BackordersPage – Eksik satırların listesi ve kapatma
====================================================
Tablo:
    * ID, Sipariş No, Stok Kodu, Eksik Adet, Ambar, Kayıt Tarihi
İşlevler:
    * Yenile ↻  – list_pending()
    * Seçiliyi Tamamla ✓ – mark_fulfilled(id)  ➜ UI & DB güncellenir
"""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt

from app.backorder import list_pending, mark_fulfilled


class BackordersPage(QWidget):
    """Bekleyen back‑order satırlarını gösterir ve tek tıkla kapatır."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.records_cache: list[dict] = []
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        lay = QVBoxLayout(self)
        title = QLabel("Back‑Order Bekleyen Satırlar")
        title.setStyleSheet("font-size:16px;font-weight:bold;padding:4px")
        lay.addWidget(title)

        # --- toolbar ----------------------------------------------------
        bar = QHBoxLayout()
        self.btn_refresh = QPushButton("↻  Yenile")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_done = QPushButton("✓  Seçiliyi Tamamla")
        self.btn_done.clicked.connect(self.complete_selected)
        bar.addWidget(self.btn_refresh); bar.addWidget(self.btn_done); bar.addStretch()
        lay.addLayout(bar)

        # --- table ------------------------------------------------------
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels([
            "ID", "Sipariş", "Stok", "Eksik", "Ambar", "Tarih"
        ])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.tbl)

    # ------------------------------------------------------------------
    def refresh(self):
        """DB'den bekleyenleri çek ve tabloyu güncelle."""
        try:
            recs = list_pending()
        except Exception as exc:
            QMessageBox.critical(self, "DB Hatası", str(exc))
            return

        self.records_cache = recs
        self.tbl.setRowCount(0)
        for r, rec in enumerate(recs):
            self.tbl.insertRow(r)
            for c, key in enumerate(["id", "order_no", "item_code", "qty_missing", "warehouse_id", "created_at"]):
                self.tbl.setItem(r, c, QTableWidgetItem(str(rec[key])))

    # ------------------------------------------------------------------
    def complete_selected(self):
        rows = {idx.row() for idx in self.tbl.selectedIndexes()}
        if not rows:
            QMessageBox.information(self, "Bilgi", "Önce satır seçin.")
            return

        ok = 0; fail = 0
        for row in rows:
            rec = self.records_cache[row]
            try:
                mark_fulfilled(rec["id"])
                ok += 1
            except Exception as exc:
                fail += 1
                QMessageBox.warning(self, "Hata", f"{rec['item_code']} : {exc}")
        self.refresh()
        QMessageBox.information(
            self, "Tamamlandı", f"{ok} kayıt kapatıldı. {(''+str(fail)+' hata.') if fail else ''}")
