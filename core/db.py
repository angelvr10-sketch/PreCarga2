"""core/db.py — Base de datos SQLite para metadatos de solicitudes."""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/solicitudes.db")


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")   # escrituras no bloquean lecturas
    return con


def init_solicitudes_db():
    """Crea las tablas si no existen."""
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS solicitudes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            numero      TEXT UNIQUE NOT NULL,
            compania    TEXT,
            n_personas  INTEGER DEFAULT 0,
            fecha_llegada TEXT,
            transporte  TEXT,
            tipo        TEXT,
            contrato    TEXT,
            activo_a    TEXT,
            activo_s    TEXT,
            tiene_bajas INTEGER DEFAULT 0,
            n_bajas     INTEGER DEFAULT 0,
            archivo     TEXT,
            procesado   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS personal (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitud_id INTEGER NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
            tipo         TEXT NOT NULL DEFAULT 'sube',   -- 'sube' | 'baja'
            rfc          TEXT,
            nombre       TEXT,
            libreta      TEXT,
            vigencia     TEXT,
            llegada      TEXT,
            salida       TEXT,
            dias         TEXT,
            transporte   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sol_numero   ON solicitudes(numero);
        CREATE INDEX IF NOT EXISTS idx_per_sol      ON personal(solicitud_id);
        CREATE INDEX IF NOT EXISTS idx_per_tipo     ON personal(tipo);
        CREATE INDEX IF NOT EXISTS idx_sol_llegada  ON solicitudes(fecha_llegada);
        """)


# ──────────────────────────────────────────────────────────────
#  Escritura
# ──────────────────────────────────────────────────────────────

def guardar_solicitud(info: dict, personal_sube: list, personal_baja: list,
                      archivo: str) -> int:
    """
    Inserta o reemplaza una solicitud con todo su personal.
    Devuelve el id de la solicitud.
    """
    procesado = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fecha_llegada = personal_sube[0]["llegada"][:10] if personal_sube else ""

    with _conn() as con:
        # Borrar si ya existe (re-procesado)
        existente = con.execute(
            "SELECT id FROM solicitudes WHERE numero=?", (info.get("numero",""),)
        ).fetchone()
        if existente:
            con.execute("DELETE FROM personal WHERE solicitud_id=?", (existente["id"],))
            con.execute("DELETE FROM solicitudes WHERE id=?", (existente["id"],))

        cur = con.execute("""
            INSERT INTO solicitudes
                (numero, compania, n_personas, fecha_llegada, transporte,
                 tipo, contrato, activo_a, activo_s,
                 tiene_bajas, n_bajas, archivo, procesado)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            info.get("solicitud", "SIN_NUM"),
            info.get("compania_corta", info.get("razonsocial", "")),
            len(personal_sube),
            fecha_llegada,
            info.get("transporte", ""),
            info.get("tipo", ""),
            info.get("contrato", ""),
            info.get("activoA") or "",
            info.get("activoS") or "",
            1 if personal_baja else 0,
            len(personal_baja),
            archivo,
            procesado,
        ))
        sol_id = cur.lastrowid

        # Personal que sube
        for p in personal_sube:
            con.execute("""
                INSERT INTO personal
                    (solicitud_id, tipo, rfc, nombre, libreta,
                     vigencia, llegada, salida, dias, transporte)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (sol_id, "sube", p.get("rfc",""), p.get("nombre",""),
                  p.get("libreta",""), p.get("vigencia",""),
                  p.get("llegada",""), p.get("salida",""),
                  p.get("dias",""), info.get("transporte","")))

        # Personal que baja
        for p in personal_baja:
            con.execute("""
                INSERT INTO personal
                    (solicitud_id, tipo, rfc, nombre, libreta,
                     vigencia, llegada, salida, dias, transporte)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (sol_id, "baja", p.get("rfc",""), p.get("nombre",""),
                  p.get("libreta",""), p.get("vigencia",""),
                  p.get("llegada",""), p.get("salida",""),
                  p.get("dias",""), info.get("transporte","")))

    return sol_id


# ──────────────────────────────────────────────────────────────
#  Lectura rápida
# ──────────────────────────────────────────────────────────────

def listar_solicitudes_db(limit: int = 200) -> list[dict]:
    """
    Devuelve solicitudes ordenadas por fecha de llegada DESC.
    Instantáneo — sin abrir ningún xlsx.
    """
    with _conn() as con:
        rows = con.execute("""
            SELECT numero, compania, n_personas, fecha_llegada,
                   transporte, tiene_bajas, n_bajas, archivo, procesado
            FROM solicitudes
            ORDER BY fecha_llegada DESC, procesado DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def listar_bajas_db() -> list[dict]:
    """Devuelve solicitudes que tienen personal de baja."""
    with _conn() as con:
        rows = con.execute("""
            SELECT numero, compania, n_bajas
            FROM solicitudes
            WHERE tiene_bajas = 1
            ORDER BY procesado DESC
        """).fetchall()
    return [dict(r) for r in rows]


def obtener_solicitud(numero: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM solicitudes WHERE numero=?", (numero,)
        ).fetchone()
    return dict(row) if row else None


def obtener_personal_sube(numero: str) -> list[dict]:
    with _conn() as con:
        sol = con.execute(
            "SELECT id FROM solicitudes WHERE numero=?", (numero,)
        ).fetchone()
        if not sol:
            return []
        rows = con.execute(
            "SELECT * FROM personal WHERE solicitud_id=? AND tipo='sube'",
            (sol["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


def obtener_personal_baja_db(numero: str) -> list[dict]:
    with _conn() as con:
        sol = con.execute(
            "SELECT id FROM solicitudes WHERE numero=?", (numero,)
        ).fetchone()
        if not sol:
            return []
        rows = con.execute(
            "SELECT rfc, nombre, transporte FROM personal WHERE solicitud_id=? AND tipo='baja'",
            (sol["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


def buscar_personal_bajas_en_bd(numeros_sol: list[str],
                                 rfcs: set[str],
                                 nombres: set[str]) -> list[dict]:
    """
    Busca en la tabla personal los registros de baja que coincidan
    con los RFC o nombres dados. Devuelve lista de dicts con
    solicitud, rfc, nombre, transporte.
    """
    if not numeros_sol:
        return []
    placeholders = ",".join("?" * len(numeros_sol))
    with _conn() as con:
        rows = con.execute(f"""
            SELECT s.numero AS solicitud, p.rfc, p.nombre, p.transporte
            FROM personal p
            JOIN solicitudes s ON s.id = p.solicitud_id
            WHERE p.tipo = 'baja'
              AND s.numero IN ({placeholders})
        """, numeros_sol).fetchall()

    resultado = []
    for r in rows:
        d = dict(r)
        vr = d.get("rfc", "").upper().strip()
        vn = d.get("nombre", "").upper().strip()
        if (vr and vr in rfcs) or (vn and vn in nombres):
            resultado.append(d)
    return resultado


def eliminar_solicitud(numero: str):
    with _conn() as con:
        con.execute("DELETE FROM solicitudes WHERE numero=?", (numero,))
