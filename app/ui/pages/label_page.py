from __future__ import annotations
"""
LabelPage – Back‑order etiket basma ekranı (sipariş bazlı)
---------------------------------------------------------
* Tarih seç → Listele : aynı gün fulfilled=1 olan back‑order kayıtlarını sipariş bazında gruplar
* Çift‑tık **veya** sağ‑tık ▸ Detayları Göster  → eksik satır listesini ve PDF Bas/Kapat düğmelerini açar
* Ana ekranda toplu seçim yapıp “Etiket Bas” ile birden fazla sipariş etiketi oluşturulabilir
"""
from pathlib import Path
from datetime import date
from typing import Dict, List

from PyQt5.QtCore import Qt, QDate, QPoint
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QMenu, QDialog, QTableWidget, QHBoxLayout
)

BASE_DIR = Path(__file__).resolve().parents[3]
import sys
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.backorder import list_fulfilled
from app.services.backorder_label_service import make_backorder_labels


class LabelPage(QWidget):
    """Back‑order etiket basma (sipariş bazlı)."""

    def __init__(self):
        super().__init__()
        self._group: Dict[str, Dict] = {}
        self._details: Dict[str, List[Dict]] = {}
        self._build_ui()

    # ---------------- UI -----------------
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<b>Back‑Order Etiket Bas</b>"))

        top = QHBoxLayout()
        self.dt = QDateEdit(QDate.currentDate())
        top.addWidget(QLabel("Tarih:"))
        top.addWidget(self.dt)

        self.spin_pkg = QSpinBox(); self.spin_pkg.setRange(1, 20); self.spin_pkg.setValue(1)
        top.addWidget(QLabel("Paket adedi (ops.):")); top.addWidget(self.spin_pkg)

        btn_list  = QPushButton("Listele");   btn_list.clicked.connect(self.refresh)
        btn_print = QPushButton("Etiket Bas"); btn_print.clicked.connect(self.print_labels)
        top.addStretch(); top.addWidget(btn_list); top.addWidget(btn_print)
        lay.addLayout(top)

        self.tbl = QTableWidget(0, 4)
        self.tbl.setHorizontalHeaderLabels(["Sipariş", "Satır", "Toplam Eksik", "İlk Tamamlama"])
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        # bağlam menüsü & çift‑tık
        self.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._show_menu)
        self.tbl.itemDoubleClicked.connect(self._show_details)
        lay.addWidget(self.tbl)

    # ----------- listele ---------------
    def refresh(self):
        on_date = self.dt.date().toPyDate().isoformat()
        rows = list_fulfilled(on_date)

        grouped: Dict[str, Dict] = {}
        details: Dict[str, List[Dict]] = {}
        for r in rows:
            g = grouped.setdefault(r["order_no"], {"satir": 0, "eksik": 0, "first": r["fulfilled_at"]})
            g["satir"] += 1
            g["eksik"] += r["qty_missing"]
            g["first"] = min(g["first"], r["fulfilled_at"])
            details.setdefault(r["order_no"], []).append(r)

        self._group = grouped
        self._details = details

        self.tbl.setRowCount(0)
        for ord_no, g in grouped.items():
            row = self.tbl.rowCount(); self.tbl.insertRow(row)
            for col, val in enumerate([ord_no, g["satir"], g["eksik"], str(g["first"])[:19]]):
                it = QTableWidgetItem(str(val)); it.setTextAlignment(Qt.AlignCenter)
                self.tbl.setItem(row, col, it)

    # ----------- toplu bas -------------
    def print_labels(self):
        if not self.tbl.selectedItems():
            QMessageBox.information(self, "Etiket", "Önce sipariş seçin")
            return
        pkg_tot = self.spin_pkg.value() or None
        for idx in {i.row() for i in self.tbl.selectedIndexes()}:
            ord_no = self.tbl.item(idx, 0).text()
            self._print_single(ord_no, pkg_tot)
        QMessageBox.information(self, "Etiket", "PDF(ler) labels/ klasörüne yazıldı.")

    # ===== Detay menu & dialog =====================================
    def _show_menu(self, pos: QPoint):
        row = self.tbl.rowAt(pos.y())
        if row < 0:
            return
        menu = QMenu(self)
        act_detail = menu.addAction("Detayları Göster")
        if menu.exec_(self.tbl.mapToGlobal(pos)) == act_detail:
            self._show_details(row)

    def _show_details(self, row_or_item):
        row = row_or_item.row() if hasattr(row_or_item, "row") else row_or_item
        ord_no = self.tbl.item(row, 0).text()
        lines = self._details.get(ord_no, [])

        dlg = QDialog(self)
        dlg.setWindowTitle(f"{ord_no} – Eksik Satırlar")

        tbl = QTableWidget(len(lines), 5)
        tbl.setHorizontalHeaderLabels(["Stok", "Eksik", "Ambar", "Tamamlama", "Back‑ID"])
        for r, ln in enumerate(lines):
            vals = [ln["item_code"], ln["qty_missing"], ln["warehouse_id"], str(ln["fulfilled_at"])[:19], ln["id"]]
            for c, v in enumerate(vals):
                it = QTableWidgetItem(str(v)); it.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(r, c, it)
        tbl.resizeColumnsToContents()
        tbl.horizontalHeader().setStretchLastSection(True)

        btn_print = QPushButton("PDF Bas")
        btn_close = QPushButton("Kapat")
        btn_print.clicked.connect(lambda: self._print_single(ord_no, self.spin_pkg.value() or None))
        btn_close.clicked.connect(dlg.accept)

        lay_btn = QHBoxLayout(); lay_btn.addStretch(); lay_btn.addWidget(btn_print); lay_btn.addWidget(btn_close)

        lay = QVBoxLayout(dlg)
        lay.addWidget(tbl); lay.addLayout(lay_btn)

        dlg.resize(650, 320)
        dlg.exec_()

    # -------- Tek PDF basıcı ----------
    def _print_single(self, order_no: str, pkg_tot: int | None):
        try:
            make_backorder_labels(
                date.today(),
                only_order=order_no,
                override_pkg_tot=pkg_tot,
                force=True
            )
        except Exception as exc:
            QMessageBox.critical(self, "Etiket", f"{order_no} hata: {exc}")
