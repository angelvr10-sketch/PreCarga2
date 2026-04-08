"""core/catalogo.py — Operaciones sobre companias.csv y activos.csv"""
import csv
from pathlib import Path
from .config import RUTA_COMPANIAS, RUTA_ACTIVOS


# ── Compañías ────────────────────────────────────────────────

def leer_companias() -> list[dict]:
    if not RUTA_COMPANIAS.exists():
        return []
    with open(RUTA_COMPANIAS, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def guardar_companias(companias: list[dict]) -> bool:
    try:
        RUTA_COMPANIAS.parent.mkdir(parents=True, exist_ok=True)
        with open(RUTA_COMPANIAS, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["razon_social", "nombre_corto"],
                               quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            w.writerows(companias)
        return True
    except Exception:
        return False


def obtener_nombre_compania(razon_social: str) -> str:
    for c in leer_companias():
        if razon_social.strip() == c.get("razon_social", "").strip():
            return c.get("nombre_corto", razon_social)
    return razon_social


# ── Activos ──────────────────────────────────────────────────

def leer_activos() -> list[str]:
    if not RUTA_ACTIVOS.exists():
        return []
    with open(RUTA_ACTIVOS, newline="", encoding="utf-8") as f:
        return [r["activo"].strip() for r in csv.DictReader(f)
                if r.get("activo", "").strip()]


def guardar_activos(activos: list[str]) -> bool:
    try:
        RUTA_ACTIVOS.parent.mkdir(parents=True, exist_ok=True)
        with open(RUTA_ACTIVOS, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            w.writerow(["activo"])
            for a in activos:
                w.writerow([a])
        return True
    except Exception:
        return False
