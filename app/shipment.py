"""
Shipment management helpers
===========================
• shipment_header   → günlük başlık (araç çıkış)   — bir sipariş × gün = 1 satır
• shipment_loaded   → Loader’da her barkod okutulduğunda eklenen kayıt (koli)

Genel API
---------
upsert_header(order_no, trip_date, pkgs_total, ...müşteri bilgileri)
    Scanner tamamlandığında / koli adedi değiştiğinde başlığı ekler | günceller.
mark_loaded(trip_id, pkg_no)
    Loader barkod okudukça pkgs_loaded ↑ ve closed durumu otomatik güncellenir.
set_trip_closed(trip_id)
    “Yükleme Tamam” butonu → closed=1 & loaded_at=GETDATE().
list_headers(), list_headers_range()
    Sevkiyat & Loader sayfalarına özet (müşteri + bölge + adres + koli) döner.
trip_by_barkod(inv_root, day)
    Barkodun kökünden (INV123‑K2) başlık satırını bulur.
"""
from __future__ import annotations

from typing import List, Dict, Any, Tuple
import os, logging
import getpass
from app.dao.logo import get_conn

from app.dao.logo import exec_sql

log    = logging.getLogger(__name__)
SCHEMA = os.getenv("SHIP_SCHEMA", "dbo")

# ────────────────────────────────────────────────────────────────
#  DDL  (ilk import’ta tabloyu yaratır/alter eder)                
# ────────────────────────────────────────────────────────────────

def _create_tables() -> None:
    """
    shipment_header      : sevkiyat başlığı  (günlük araç çıkışı – 1 sipariş × gün)
    shipment_loaded      : her koli barkodu okunduğunda eklenen satır
    Fonksiyon tekrar çağrılsa bile yalnızca eksik kolonlar ALTER edilir.
    """
    ddl = f"""
    /* ───────────── shipment_header ───────────── */
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE name='shipment_header')
    CREATE TABLE {SCHEMA}.shipment_header(
        id             INT IDENTITY PRIMARY KEY,
        trip_date      DATE            NOT NULL,
        order_no       NVARCHAR(32)    NOT NULL,
        customer_code  NVARCHAR(32)    NULL,
        customer_name  NVARCHAR(128)   NULL,
        region         NVARCHAR(64)    NULL,
        address1       NVARCHAR(255)   NULL,
        pkgs_total     INT             NOT NULL,
        pkgs_loaded    INT             DEFAULT 0,
        closed         BIT             DEFAULT 0,
        loaded_at      DATETIME        NULL,          -- araç çıkış anı
        invoice_root   NVARCHAR(32)    NULL,          -- CAN2025…   (K-siz kök)
        qr_token       NVARCHAR(64)    NULL,          -- QR pdf’leri için
        printed        BIT             DEFAULT 0,     -- pdf/etiket basıldı mı?
        created_at     DATETIME        DEFAULT GETDATE(),
        UNIQUE(trip_date, order_no)
    );

    /* eksik kolonları sonradan ekle -- idempotent */
    IF NOT EXISTS (SELECT * FROM sys.columns
                   WHERE Name='invoice_root'
                     AND Object_ID = Object_ID('{SCHEMA}.shipment_header'))
        ALTER TABLE {SCHEMA}.shipment_header
            ADD invoice_root NVARCHAR(32) NULL;

    IF NOT EXISTS (SELECT * FROM sys.columns
                   WHERE Name='qr_token'
                     AND Object_ID = Object_ID('{SCHEMA}.shipment_header'))
        ALTER TABLE {SCHEMA}.shipment_header
            ADD qr_token NVARCHAR(64) NULL;

    IF NOT EXISTS (SELECT * FROM sys.columns
                   WHERE Name='printed'
                     AND Object_ID = Object_ID('{SCHEMA}.shipment_header'))
        ALTER TABLE {SCHEMA}.shipment_header
            ADD printed BIT DEFAULT 0;

    /* ───────────── shipment_loaded ───────────── */
    IF NOT EXISTS (SELECT * FROM sys.objects WHERE name='shipment_loaded')
    CREATE TABLE {SCHEMA}.shipment_loaded(
        id          INT IDENTITY PRIMARY KEY,
        trip_id     INT            REFERENCES {SCHEMA}.shipment_header(id),
        pkg_no      INT            NOT NULL,
        loaded      BIT            DEFAULT 0,        -- 0=okutulmadı  1=okundu
        loaded_by   NVARCHAR(64)   NULL,
        loaded_time DATETIME       NULL,
        UNIQUE(trip_id, pkg_no)
    );

    /* eksik kolonlar */
    IF NOT EXISTS (SELECT * FROM sys.columns
                   WHERE Name='loaded'
                     AND Object_ID = Object_ID('{SCHEMA}.shipment_loaded'))
        ALTER TABLE {SCHEMA}.shipment_loaded
            ADD loaded BIT DEFAULT 0;

    IF NOT EXISTS (SELECT * FROM sys.columns
                   WHERE Name='loaded_by'
                     AND Object_ID = Object_ID('{SCHEMA}.shipment_loaded'))
        ALTER TABLE {SCHEMA}.shipment_loaded
            ADD loaded_by NVARCHAR(64) NULL;

    IF NOT EXISTS (SELECT * FROM sys.columns
                   WHERE Name='loaded_time'
                     AND Object_ID = Object_ID('{SCHEMA}.shipment_loaded'))
        ALTER TABLE {SCHEMA}.shipment_loaded
            ADD loaded_time DATETIME NULL;
    """
    with get_conn(autocommit=True) as cn:
        cn.execute(ddl)

    log.info("shipment_header / shipment_loaded tabloları hazır")


_create_tables()

# ────────────────────────────────────────────────────────────────
#  Header upsert – Scanner tamamlayınca                         
# ────────────────────────────────────────────────────────────────
def upsert_header(
    order_no: str,
    trip_date: str,
    pkgs_total: int,
    *,
    customer_code: str = "",
    customer_name: str = "",
    region: str = "",
    address1: str = "",
    invoice_root: str | None = None,
) -> None:

    sql = f"""
    MERGE {SCHEMA}.shipment_header AS tgt
    USING (SELECT ? AS trip_date, ? AS order_no) src
      ON (tgt.trip_date = src.trip_date AND tgt.order_no = src.order_no)
    WHEN MATCHED THEN
        /* 🔸 SADECE BÜYÜT:  max(pkgs_total, yeni_değer) */
        UPDATE SET pkgs_total = CASE WHEN ? > tgt.pkgs_total
                                     THEN ? ELSE tgt.pkgs_total END,
                   closed     = 0,
                   invoice_root = COALESCE(tgt.invoice_root, ?)
    WHEN NOT MATCHED THEN
        INSERT (trip_date, order_no, pkgs_total,
                customer_code, customer_name, region, address1, invoice_root)
        VALUES (?,?,?,?,?,?,?,?);
    """

    with get_conn(autocommit=True) as cn:
        cn.execute(
            sql,
            # ---------- src ----------
            trip_date, order_no,
            # ---------- UPDATE ----------
            pkgs_total, pkgs_total, invoice_root,
            # ---------- INSERT ----------
            trip_date, order_no, pkgs_total,
            customer_code, customer_name, region, address1, invoice_root
        )




# ────────────────────────────────────────────────────────────────
#  “Yükleme Tamam”  butonu                                       
# ────────────────────────────────────────────────────────────────

def set_trip_closed(trip_id: int, closed: bool=True) -> None:
    sql = f"""
        UPDATE {SCHEMA}.shipment_header
           SET closed   = ?,
               en_route = ?,
               loaded_at = CASE WHEN ?=1 THEN GETDATE() ELSE loaded_at END
         WHERE id = ?"""
    with get_conn(autocommit=True) as cn:
        cn.execute(sql, int(closed), int(closed), int(closed), trip_id)

        # 🔸 EK: loglama
        pkgs_loaded, pkgs_total = cn.execute(
            "SELECT pkgs_loaded, pkgs_total FROM shipment_header WHERE id=?",
            trip_id
        ).fetchone()
        if closed:
            action = ("TRIP_AUTO_CLOSED" if pkgs_loaded == pkgs_total
                      else "TRIP_MANUAL_CLOSED_INCOMPLETE")
            exec_sql("""
                INSERT INTO USER_ACTIVITY
                (username, action, details, order_no)
                SELECT ?, ?, ?, order_no
                  FROM shipment_header WHERE id=?""",
                getpass.getuser(), action,
                f"{pkgs_loaded}/{pkgs_total}", trip_id)

# ────────────────────────────────────────────────────────────────
#  UI Query helpers                                              
# ────────────────────────────────────────────────────────────────

def _fetch(sql: str, *params) -> List[Dict[str,Any]]:
    with get_conn() as cn:
        cur = cn.execute(sql, *params)
        cols = [c[0].lower() for c in cur.description]
        return [dict(zip(cols,row)) for row in cur.fetchall()]

def fetch_one(sql: str, *params) -> Dict[str, Any] | None:
    with get_conn() as cn:
        cur = cn.execute(sql, *params)
        row = cur.fetchone()
        if row is None:
            return None
        cols = [c[0].lower() for c in cur.description]
        return dict(zip(cols, row))

def list_headers(trip_date: str) -> List[Dict[str,Any]]:
    sql = f"""
        SELECT id, order_no, customer_code, customer_name, region, address1,
               pkgs_total, pkgs_loaded, closed,
               CONVERT(char(19), created_at, 120) AS created_at,
               CONVERT(char(19), loaded_at, 120) AS loaded_at
          FROM {SCHEMA}.shipment_header
         WHERE trip_date = ?
         ORDER BY id DESC"""  # en son sevkiyat en üstte
    return _fetch(sql, trip_date)

def list_headers_range(start: str, end: str) -> List[Dict[str,Any]]:
    sql = f"""
        SELECT trip_date, id, order_no, customer_code, customer_name, region, address1,
               pkgs_total, pkgs_loaded, closed,
               CONVERT(char(19), created_at, 120) AS created_at,
               CONVERT(char(19), loaded_at, 120) AS loaded_at
          FROM {SCHEMA}.shipment_header
         WHERE trip_date BETWEEN ? AND ?
         ORDER BY id DESC"""    # en son sevkiyat en üstte
    return _fetch(sql, start, end)

# Eski alias’lar
lst_headers     = list_headers
lst_trp_lines   = list_headers
lst_headers_rng = list_headers_range

# ────────────────────────────────────────────────────────────────
#  Shipment barkod okutma – barkod kökünden trip_id bulma
# ----------------------------------------------------------------------
# Tek barkoddan (CAN… / ARV…) aktif sevkiyat (= henüz dolmamış başlık) bul
# ----------------------------------------------------------------------
def trip_by_barkod(inv_root: str, day: str | None = None):
    """
    Barkod köküne (invoice_root) göre, hâlâ boş koli(leri) bulunan
    açık sevkiyat başlığını döndürür.

    Parametreler
    ------------
    inv_root : str
        Barkodun “-K” öncesi kısmı (CAN202500000123 gibi).
    day : str | None
        'YYYY-MM-DD' biçiminde tarih filtre­si. None => tarih bakma.

    Döndürür
    --------
    tuple[int, int] | None
        (trip_id, pkgs_total)  veya  None (eşleşme yoksa)
    """
    sql = """
        SELECT TOP (1) id, pkgs_total
        FROM   shipment_header
        WHERE  invoice_root = ?
          AND  closed        = 0
          AND  pkgs_loaded  < pkgs_total      -- 🔸 hâlâ eksik koli var
    """
    params: list = [inv_root]
    if day:
        sql += " AND CAST(created_at AS DATE) = ?"
        params.append(day)

    sql += " ORDER BY id"                     # en eski / düşük id öncelik
    row = fetch_one(sql, *params)
    return (row["id"], row["pkgs_total"]) if row else None


# ────────────────────────────────────────────────────────────────
#  Loader barkod → “yüklendi”
#  (pkgs_total değerine DOKUNMAZ!)
# ────────────────────────────────────────────────────────────────
def mark_loaded(trip_id: int, pkg_no: int, *, item_code: str | None = None):
    """
    • Aynı barkod ikinci kez okutulursa sayaç artmaz → 0 döner.
    • Koli sayımı (pkgs_loaded) trg_loaded_aiu tetikleyicisiyle yapılır.
    • pkgs_total değişTİRİLMEZ; yalnızca eksikse tetikleyici genişletir.
    • Başarı: 1   |   Yinelenen okuma: 0
    • Tüm koliler tamamlandığında otomatik olarak set_trip_closed()
      çağrılır, en_route=1 olur ve USER_ACTIVITY’ye log düşülür.
    """
    with get_conn(autocommit=True) as cn:

        # 1) Barkod zaten yüklendi mi?
        row = cn.execute(
            "SELECT loaded FROM shipment_loaded "
            "WHERE trip_id = ? AND pkg_no = ?", trip_id, pkg_no
        ).fetchone()
        if row and row[0] == 1:
            return 0    # ikinci kez okundu

        # 2) INSERT veya UPDATE  → loaded = 1
        if row:      # satır var, loaded = 0
            cn.execute(
                """UPDATE shipment_loaded
                     SET loaded      = 1,
                         loaded_by   = ?,
                         loaded_time = GETDATE()
                   WHERE trip_id = ? AND pkg_no = ?""",
                getpass.getuser(), trip_id, pkg_no
            )
        else:        # satır yok
            cn.execute(
                """INSERT INTO shipment_loaded
                       (trip_id, pkg_no, loaded, loaded_by, loaded_time)
                     VALUES (?,?,1,?,GETDATE())""",
                trip_id, pkg_no, getpass.getuser()
            )

        # 3) Opsiyonel – ilgili stok satırını işaretle
        if item_code:
            cn.execute(
                """
                UPDATE shipment_lines
                   SET loaded = 1
                 WHERE order_no = (SELECT order_no
                                     FROM shipment_header
                                    WHERE id = ?)
                   AND item_code = ?""",
                trip_id, item_code
            )

        # 4) Tüm koliler tamam mı?  → otomatik “Yükleme Tamam”
        pkgs_loaded, pkgs_total = cn.execute(
            "SELECT pkgs_loaded, pkgs_total FROM shipment_header WHERE id=?",
            trip_id
        ).fetchone()

        if pkgs_loaded == pkgs_total:
            # en_route = 1, closed = 1
            set_trip_closed(trip_id, True)

            # LOG — geç tamamlanmışsa ayrı eylem adı
            action = ("TRIP_AUTO_CLOSED"
                      if pkgs_loaded == pkg_no == pkgs_total
                      else "TRIP_COMPLETED_LATE")
            exec_sql("""
                INSERT INTO USER_ACTIVITY
                    (username, action, details, order_no)
                SELECT ?, ?, ?, order_no
                  FROM shipment_header WHERE id=?""",
                getpass.getuser(), action,
                f"{pkgs_loaded}/{pkgs_total}", trip_id
            )

    return 1
# ────────────────────────────────────────────────────────────────
