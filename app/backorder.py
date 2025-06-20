"""
backorder.py – Eksik satır & sevkiyat kayıtları
==============================================

 • İki yardımcı tablo oluşturur:
      dbo.backorders       –  eksik (missing) satırlar
      dbo.shipment_lines   –  gönderilen (shipped) satırlar
 • insert_backorder      → eksik satır ekle / güncelle
 • add_shipment          → sevk satırı ekle / güncelle
 • create_tables() ilk import’ta otomatik çalışır
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any
import logging, os

from app.dao.logo import get_conn   # aynı ODBC bağlantısını kullanıyoruz

_log = logging.getLogger(__name__)
SCHEMA = os.getenv("BACKORDER_SCHEMA", "dbo")

# -------------------------------------------------------------------- #
#  TABLOLARI OLUŞTUR – yalnızca ilk import’ta                                 #
# -------------------------------------------------------------------- #
def create_tables() -> None:
    ddl = f"""
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE name='backorders')
    CREATE TABLE {SCHEMA}.backorders(
        id           INT IDENTITY PRIMARY KEY,
        order_no     NVARCHAR(32),
        line_id      INT,
        warehouse_id INT,
        item_code    NVARCHAR(64),
        qty_missing  FLOAT,
        eta_date     DATE NULL,
        fulfilled    BIT         DEFAULT 0,
        created_at   DATETIME    DEFAULT GETDATE(),
        fulfilled_at DATETIME    NULL
    );

    IF NOT EXISTS (SELECT * FROM sys.objects WHERE name='shipment_lines')
    CREATE TABLE {SCHEMA}.shipment_lines(
        id            INT IDENTITY PRIMARY KEY,
        invoice_no    NVARCHAR(32),     -- bizde sipariş no
        item_code     NVARCHAR(64),
        warehouse_id  INT,
        invoiced_qty  FLOAT,
        qty_shipped   FLOAT     DEFAULT 0,
        loaded        BIT         DEFAULT 0,
        last_update   DATETIME    DEFAULT GETDATE()
    );
    
    -- Mevcut tabloya loaded kolonu ekle (eğer yoksa)
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('{SCHEMA}.shipment_lines') AND name = 'loaded')
    ALTER TABLE {SCHEMA}.shipment_lines ADD loaded BIT DEFAULT 0;
    """
    with get_conn(autocommit=True) as cn:
        cn.execute(ddl)
    _log.info("backorders / shipment_lines tabloları hazır.")

# İlk import’ta tablo var mı diye kontrol et
create_tables()

# -------------------------------------------------------------------- #
#  BACK-ORDER KAYITLARI                                                #
# -------------------------------------------------------------------- #
def insert_backorder(order_no:str, line_id:int, warehouse_id:int,
                     item_code:str, qty_missing:float, eta_date:Optional[str]=None):
    """
    Aynı sipariş + stok için kayıt varsa qty_missing ↑ artar (idempotent).
    """
    sql_sel = f"""SELECT id, qty_missing FROM {SCHEMA}.backorders
                  WHERE fulfilled=0 AND order_no=? AND item_code=?"""
    sql_ins = f"""INSERT INTO {SCHEMA}.backorders
                  (order_no,line_id,warehouse_id,item_code,qty_missing,eta_date)
                  VALUES (?,?,?,?,?,?)"""
    sql_upd = f"""UPDATE {SCHEMA}.backorders
                  SET qty_missing = qty_missing + ?
                  WHERE id=?"""
    with get_conn(autocommit=True) as cn:
        row = cn.execute(sql_sel, order_no, item_code).fetchone()
        if row:
            cn.execute(sql_upd, qty_missing, row.id)
        else:
            cn.execute(sql_ins,
                       order_no,line_id,warehouse_id,item_code,qty_missing,eta_date)

def add_shipment(order_no: str,          # sipariş / fatura kökü
                 trip_date: str,         # YYYY-MM-DD  → gün anahtarı
                 item_code: str,
                 warehouse_id: int,
                 invoiced_qty: float,    # Logo’daki fatura adedi
                 qty_delta: float):      # bu sevk-tamamlama ile gönderilen

    """
    • Aynı (order_no + item_code) satırı varsa
      qty_shipped alanını artırır.
    • Yoksa yeni satır açar.
    • trip_date parametresi backward compatibility için korunuyor
    """

    sql = f"""
    MERGE {SCHEMA}.shipment_lines AS tgt
    USING (SELECT
              ? AS invoice_no,
              ? AS item_code) src
      ON  tgt.invoice_no = src.invoice_no
      AND tgt.item_code  = src.item_code
    WHEN MATCHED THEN
        UPDATE
           SET qty_shipped = qty_shipped + ?,
               last_update = GETDATE()
    WHEN NOT MATCHED THEN
        INSERT (invoice_no, item_code,
                warehouse_id, invoiced_qty, qty_shipped,
                last_update)
        VALUES (?,?,?,?,?,GETDATE());
    """

    with get_conn(autocommit=True) as cn:
        cn.execute(sql,
                   order_no, item_code,              # src
                   qty_delta,                        # UPDATE
                   order_no, item_code,              # INSERT
                   warehouse_id, invoiced_qty, qty_delta)


# -------------------------------------------------------------------- #
#  YARDIMCI LİSTELER                                                   #
# -------------------------------------------------------------------- #
def list_pending() -> List[Dict[str,Any]]:
    sql = f"SELECT * FROM {SCHEMA}.backorders WHERE fulfilled=0"
    with get_conn() as cn:
        cur = cn.execute(sql)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols,row)) for row in cur.fetchall()]

def mark_fulfilled(back_id:int):
    sql = f"""UPDATE {SCHEMA}.backorders
              SET fulfilled=1, fulfilled_at=GETDATE() WHERE id=?"""
    with get_conn(autocommit=True) as cn:
        cn.execute(sql, back_id)


# --------------------------------------------------------------------
#  Tamamlanmış eksikler – listele
# --------------------------------------------------------------------
def list_fulfilled(on_date: Optional[str] = None) -> List[Dict[str, Any]]:
    sql = f"SELECT * FROM {SCHEMA}.backorders WHERE fulfilled = 1"
    if on_date:
        # güvenlik / performans için parametreli ver
        sql += " AND CAST(fulfilled_at AS DATE) = ?"
        params = (on_date,)
    else:
        params = ()
    with get_conn() as cn:
        cur = cn.execute(sql, *params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

