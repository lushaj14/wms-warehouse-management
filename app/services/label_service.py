"""
label_service.py – V6 (CAN Otomotiv, 100 × 100 mm + Footer)
====================================================
• Tek PDF → çok sayfa (koli adedi)
• Sayfa boyutu **100 mm × 100 mm**
• DejaVu Sans Unicode font gömülü → Türkçe karakter sorunu yok
• Barkod, fatura no, tarih, transfer vb.
• Dinamik footer desteği: tüm etiketlerin en altına ortalanmış metin eklenebilir

Kullanım
--------
```bash
python -m app.services.label_service --order-no SO2025-000202
python -m app.services.label_service --order-no SO2025-000202 --force
```
`--force`: Fatura yoksa sipariş no barkodlanır

Ek argüman
----------
`--footer "METİN"` : Etiket altına ortalanmış footer metni

Env vars
--------
FONT_PATH = "app/fonts/DejaVuSans.ttf"
LABEL_OUT_DIR (default: ./labels)
"""
from __future__ import annotations

import os, sys, re, logging, argparse, datetime as dt
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

try:
    from app.dao import logo as dao
    from app.core.auth import get_current_user
    from app.core.logger import get_logger, log_user_action
except ModuleNotFoundError:
    import dao.logo as dao
    get_current_user = lambda: None
    get_logger = lambda x: logging.getLogger(x)
    log_user_action = lambda *args, **kwargs: None

import pyodbc
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")

# ---------------------------------------------------------------------------
COMPANY_TEXT = "CAN OTOMOTIV"
PAGE_SIZE    = (100*mm, 100*mm)
OUT_DIR      = Path(os.getenv("LABEL_OUT_DIR", "labels"))
OUT_DIR.mkdir(exist_ok=True)
FONT_PATH    = os.getenv("FONT_PATH", str(BASE_DIR/"fonts"/"DejaVuSans.ttf"))

try:
    pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))
    FONT_NAME = "DejaVu"
except Exception:
    logging.warning("DejaVuSans.ttf bulunamadı; Helvetica kullanılacak")
    FONT_NAME = "Helvetica"

# ---------------------------------------------------------------------------
def parse_int(text: str, default:int=1) -> int:
    m = re.search(r"(\d+)", text or "")
    return int(m.group(1)) if m else default

# ---------------------------------------------------------------------------
def fetch_invoice_no(order_no: str) -> Optional[str]:
    """Fatura no al (CAN*/ARV* öncelikli)"""
    sqls = [
        f"""
        SELECT TOP 1 I.FICHENO
        FROM {dao._t('INVOICE')} I
        JOIN {dao._t('STLINE')} S ON S.INVOICEREF = I.LOGICALREF
        WHERE S.ORDFICHEREF IN (
              SELECT LOGICALREF FROM {dao._t('ORFICHE')} WHERE FICHENO = ?)
          AND I.CANCELLED = 0
          AND (I.FICHENO LIKE 'CAN%' OR I.FICHENO LIKE 'ARV%')
        """,
        f"""
        SELECT TOP 1 FICHENO
        FROM {dao._t('INVOICE')}
        WHERE SPECODE = ? AND CANCELLED=0
        """,
    ]
    with dao.get_conn() as cn:
        for sql in sqls:
            try:
                row = cn.execute(sql, order_no).fetchone()
                if row:
                    return row[0]
            except pyodbc.ProgrammingError:
                continue
    return None

# ---------------------------------------------------------------------------
def draw_page(c: canvas.Canvas, p: Dict[str, str]):
    """Tek koli etiketi (100×100 mm) çizer"""
    x = 6*mm
    y = 93*mm

    # Başlık & bölge
    c.setFont(FONT_NAME, 14)
    c.drawString(x, y, COMPANY_TEXT)
    c.setFont(FONT_NAME, 10)
    c.drawRightString(PAGE_SIZE[0]-x, y, "GEREDE")

    y -= 6*mm
    c.setFont(FONT_NAME, 8)
    c.drawRightString(PAGE_SIZE[0]-x, y, p["region"])

    # Cari kodu & adı
    y -= 10*mm
    c.setFont(FONT_NAME, 8)
    c.drawString(x, y, p["cari_kodu"])
    y -= 5*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(x, y, p["cari_adi"])

    # Adres
    c.setFont(FONT_NAME, 8)
    for line in p["adres_lines"]:
        y -= 4*mm
        c.drawString(x, y, line)

    # Sipariş No & Koli
    y -= 6*mm
    c.setFont(FONT_NAME, 10)
    c.drawString(x, y, f"Sipariş No: {p['order_no']}")
    c.drawRightString(PAGE_SIZE[0]-x, y, f"Koli: {p['pkg_no']}/{p['pkg_tot']}")

    # Barkod
    y -= 20*mm
    bc = code128.Code128(p["barkod"], barHeight=12*mm, barWidth=0.825)
    bc_x = (PAGE_SIZE[0] - bc.width) / 2
    bc.drawOn(c, bc_x, y)

    # Barkod altı fatura no
    y -= 7*mm
    c.setFont(FONT_NAME, 8)
    c.drawCentredString(PAGE_SIZE[0]/2, y, p["barkod"])

    # Sipariş tarihi & transfer
    y -= 6*mm
    c.setFont(FONT_NAME, 7)
    c.drawString(x, y, f"Sipariş Tarihi: {p['sip_tarih']}")
    if p.get("transfer"):
        c.drawRightString(PAGE_SIZE[0]-x, y, f"Transfer: {p['transfer']}")

    # İlk sayfa için fatura hatırlatma metni
    if p.get("inv_line"):
        y -= 8*mm
        c.setFont(FONT_NAME, 9)
        c.drawCentredString(PAGE_SIZE[0]/2, y, p["inv_line"])

    # Footer (ör: "EKSİK GÖNDERİLEN SEVKİYAT")
    if p.get("footer"):
        c.setFont(FONT_NAME, 8)
        c.drawCentredString(PAGE_SIZE[0]/2, 5*mm, p["footer"])

    c.showPage()


# ---------------------------------------------------------------------------
def make_labels(order_no: str, *, force: bool = False, footer: str = ""):
    """
    • Her paket için barkod  →  FaturaNo-K1 , FaturaNo-K2 …
    • force=True  → fatura yoksa da sipariş no kullanılır.
    """
    hdr = dao.fetch_order_header(order_no)
    if not hdr:
        logging.error("Sipariş bulunamadı: %s", order_no)
        sys.exit(1)

    invoice_no = fetch_invoice_no(order_no)
    if not invoice_no and not force:
        logging.warning("Fatura yok – basılmadı")
        sys.exit(1)

    barkod_root = invoice_no or order_no           # ← temel kısım
    pkg_tot     = parse_int(hdr.get("genexp4", "1"))

    pdf_path = OUT_DIR / f"LABEL_{dt.datetime.now():%Y%m%d_%H%M%S}_{order_no}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=PAGE_SIZE)

    # — adres satırlarını kır —
    adres_raw   = (hdr.get("adres", "").upper()).split()
    adres_lines = [" ".join(adres_raw[i:i + 6]) for i in range(0, len(adres_raw), 6)][:2]
    
    # Footer'a kullanıcı bilgisi ekle
    current_user = get_current_user()
    user_info = ""
    if current_user:
        user_info = f"Hazırlayan: {current_user.get('full_name', current_user.get('username', 'N/A'))}"
    
    # Footer'ı birleştir
    combined_footer = footer
    if user_info:
        combined_footer = f"{footer} | {user_info}" if footer else user_info

    for i in range(1, pkg_tot + 1):
        barkod = f"{barkod_root}-K{i}"             # ← 🔸 YENİ: paket no ekle

        payload = {
            "order_no":   order_no,
            "pkg_no":     i,
            "pkg_tot":    pkg_tot,
            "barkod":     barkod,                  # ← güncel barkod
            "cari_kodu":  hdr.get("cari_kodu", ""),
            "cari_adi":   hdr.get("cari_adi", "")[:30],
            "adres_lines": adres_lines,
            "region":     f"{hdr.get('genexp2','')} - {hdr.get('genexp3','')}".strip(" -"),
            "sip_tarih":  dt.datetime.now().strftime("%d-%m-%Y"),
            "transfer":   hdr.get("genexp1", "").strip(";"),
            "inv_line":   "FATURA BU PAKETİN İÇİNDEDİR" if i == 1 else "",
            "footer":     combined_footer,
        }
        draw_page(c, payload)

    c.save()
    
    # User activity log
    log_user_action(
        "LABEL_PRINT",
        f"Etiket yazdırıldı",
        order_no=order_no,
        package_count=pkg_tot,
        pdf_path=str(pdf_path)
    )
    
    logging.info("PDF etiketi oluşturuldu → %s", pdf_path)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="CAN Otomotiv etiket PDF")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--order-no", "--order", help="Sipariş no (FICHENO)")
    grp.add_argument("--id", type=int, help="Sipariş LOGICALREF")
    ap.add_argument("--force", action="store_true", help="Fatura yoksa da bastır")
    ap.add_argument("--footer", default="", help="Etiket altına ortalanacak metin")
    args = ap.parse_args()

    ord_no = args.order_no or dao.fetch_order_no_by_id(args.id)
    if not ord_no:
        logging.error("Sipariş no bulunamadı!"); sys.exit(1)

    make_labels(ord_no, force=args.force, footer=args.footer)

if __name__ == "__main__":
    main()
