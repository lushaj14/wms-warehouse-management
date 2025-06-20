#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────
#  Kalıcı ayar yönetimi (JSON)  –  app/settings.py
# ──────────────────────────────────────────────────────────────
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[2]
CFG_PATH = BASE_DIR / "settings.json"

# ───────────── Varsayılanlar ─────────────
DEFAULTS: Dict[str, Any] = {
    "ui": {
        "theme":      "light",
        "font_pt":    10,
        "toast_secs": 3,
        "lang":       "TR",
        "sounds": {
            "enabled": True,
            "volume":  0.9       # 0-1
        },
        "auto_focus": True
    },
    "scanner": {
        "prefixes": {"D1-": "0", "D3-": "1"},
        "over_scan_tol": 0
    },
    "loader": {
        "auto_refresh": 30,
        "block_incomplete": True
    },
    "db": {
        "server":    "78.135.108.160,1433",
        "database":  "logo",
        "user":      "barkod1",
        "retry":     3,
        "heartbeat": 10
    },
    "paths": {
        "label_dir":  str(BASE_DIR / "labels"),
        "export_dir": str(Path.home() / "Desktop"),
        "log_dir":    str(BASE_DIR / "logs")
    },
    "print": {
        "label_printer": "",   # Zebra / TSC … (etiket)
        "doc_printer":   "",   # A4 PDF yazıcı
        "label_tpl":     "default.tpl",
        "auto_open":     True
    }
}

# ───────────── Yardımcılar ─────────────
_cfg: Dict[str, Any] = {}


def _deep_update(dst: Dict, src: Dict) -> None:
    """src içeriğini dst’ye (recursive) ekle / güncelle."""
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k, {}), dict):
            _deep_update(dst.setdefault(k, {}), v)
        else:
            dst[k] = v


def _load_disk() -> Dict[str, Any]:
    """config.json oku – hata varsa boş sözlük döndür."""
    if not CFG_PATH.exists():
        return {}
    try:
        with CFG_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        # bozuk dosyayı .bak yap, defaults’a dön
        try:
            CFG_PATH.rename(CFG_PATH.with_suffix(".bak"))
        except Exception:
            pass
        print(f"[settings] Uyarı: config.json bozuk, yedek alındı ({exc})")
        return {}

# ───────────── Ana API ─────────────
def reload() -> Dict[str, Any]:
    """
    Defaults + disk’teki ayarları birleştir.
    *scanner.prefixes* disk’te tanımlıysa (boş sözlük bile olsa)
    **tamamen** disk’teki hali kullanılır.
    """
    global _cfg
    _cfg = {}
    _deep_update(_cfg, DEFAULTS)        # 1) varsayılanlar

    disk = _load_disk()                 # 2) kullanıcı JSON
    _deep_update(_cfg, disk)

    # --- OVERRIDE: scanner.prefixes tam sözlük olarak ele al ----
    if isinstance(disk.get("scanner", {}).get("prefixes"), dict):
        _cfg["scanner"]["prefixes"] = disk["scanner"]["prefixes"]
    # ------------------------------------------------------------

    return _cfg


# geriye-uyumluluk: eski kodlarda settings.load() varsa bozulmasın
load = reload


def save() -> None:
    """Bellekteki ayarları diske yazar (pretty JSON)."""
    try:
        with CFG_PATH.open("w", encoding="utf-8") as f:
            json.dump(_cfg, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[settings] Kaydetme hatası: {exc}")


def get(path: str, default: Any = None) -> Any:
    """'ui.theme' gibi noktalı yolu okuyup değeri döndürür."""
    cur = _cfg
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return default
    return cur


def set(path: str, value: Any) -> None:
    """'db.retry', 5 → değeri güncelle & otomatik kaydet."""
    parts = path.split(".")
    cur = _cfg
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value
    save()

# ───────────── İlk yükleme ─────────────
reload()


# — Basit CLI testi —
if __name__ == "__main__":
    from pprint import pprint
    print("Tema:", get("ui.theme"))
    set("ui.theme", "dark")
    pprint(_cfg)
