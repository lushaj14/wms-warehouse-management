"""
CSV / Excel → barcode_xref toplu içe aktarma
-------------------------------------------
Kullanım:
    from app.services.import_barcodes import load_file
    ok, sec, err = load_file("dosya.csv")
"""

from pathlib import Path
import time, csv
from typing import List, Tuple

import pandas as pd                       # openpyxl + xlrd kurulu olmalı
from app.dao.logo import get_connection    # DAO’daki ortak bağlantı

# ────────────────────────────────────────────────────────────────────────────
# MERGE  →  varsa UPDATE  |  yoksa INSERT
# ────────────────────────────────────────────────────────────────────────────
SQL = (
    "MERGE dbo.barcode_xref AS tgt "
    "USING (VALUES (?, ?, ?, ?)) "
    "     AS src(barcode, wh, item_code, mul) "
    "ON (tgt.barcode = src.barcode AND tgt.warehouse_id = src.wh) "
    "WHEN MATCHED THEN "
    "     UPDATE SET tgt.item_code   = src.item_code, "
    "                tgt.multiplier  = src.mul, "
    "                tgt.updated_at  = GETDATE() "
    "WHEN NOT MATCHED THEN "
    "     INSERT (barcode, warehouse_id, item_code, multiplier, updated_at) "
    "     VALUES (src.barcode, src.wh, src.item_code, src.mul, GETDATE());"
)

# ────────────────────────────────────────────────────────────────────────────
# Dosya okuma yardımcıları
# ────────────────────────────────────────────────────────────────────────────
def _read_csv(path: Path) -> List[Tuple]:
    with open(path, newline="", encoding="utf-8") as f:
        return [(
            r["barcode"].strip(),
            int(r["warehouse_id"]),
            r["item_code"].strip(),
            float(r.get("multiplier") or 1),
        ) for r in csv.DictReader(f)]


def _read_xlsx(path: Path) -> List[Tuple]:
    df = pd.read_excel(path, dtype=str)
    df["multiplier"] = df.get("multiplier", 1).fillna(1).astype(float)
    return list(zip(
        df["barcode"].str.strip(),
        df["warehouse_id"].astype(int),
        df["item_code"].str.strip(),
        df["multiplier"]
    ))

# ────────────────────────────────────────────────────────────────────────────
# Ana fonksiyon
# ────────────────────────────────────────────────────────────────────────────
def load_file(path: str) -> Tuple[int, float, int]:
    """
    path : CSV / XLSX dosya yolu

    Döner ⇒ (işlenen satır sayısı, geçen süre sn, hata adedi)
    """
    path = Path(path)
    rows = _read_csv(path) if path.suffix.lower() == ".csv" else _read_xlsx(path)

    conn = get_connection(False)          # tek transaction
    cur  = conn.cursor(); cur.fast_executemany = True

    t0 = time.time(); err = 0
    try:
        cur.executemany(SQL, rows)        # tek seferde bütün satırlar
        conn.commit()
        done = len(rows)
        conn.close()
    except Exception as exc:
        conn.rollback(); conn.close()
        err  = 1
        done = 0
        print(f"[import_barcodes] Hata: {exc}")

    return done, time.time() - t0, err
