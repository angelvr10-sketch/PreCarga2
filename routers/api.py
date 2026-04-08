"""routers/api.py — Endpoints de acción: upload, procesamiento, descarga"""
import csv
import io
import json
import uuid
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from core import (
    llenar_plantilla, leer_personal_de_xlsx,
    llenar_plantilla_entrada, llenar_plantilla_salidas,
    listar_archivos_baja,
    logger, SOL_DIR, LOGS_DIR,
)
from core.config import RUTA_PLANTILLA_SALIDA, RUTA_PLANTILLA_ENTRADA

router = APIRouter(prefix="/api")

# Almacén temporal de BDs cargadas (en memoria, por token)
_bd_store: dict[str, dict] = {}


# ── Procesar PDF ──────────────────────────────────────────────
@router.post("/procesar-pdf")
async def procesar_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"ok": False, "mensaje": "Solo se aceptan archivos PDF"})
    try:
        contenido = await file.read()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(contenido)
            ruta_tmp = Path(tmp.name)

        exito, mensaje = llenar_plantilla(ruta_tmp)
        ruta_tmp.unlink(missing_ok=True)
        return JSONResponse({"ok": exito, "mensaje": mensaje})

    except Exception as e:
        logger.error(f"Error en /api/procesar-pdf: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Cargar BD de personal ─────────────────────────────────────
@router.post("/cargar-bd")
async def cargar_bd(file: UploadFile = File(...)):
    try:
        contenido = await file.read()
        texto = contenido.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(texto))
        columnas = list(reader.fieldnames or [])
        filas    = list(reader)

        token = str(uuid.uuid4())
        _bd_store[token] = {"columnas": columnas, "filas": filas}

        return JSONResponse({"ok": True, "token": token, "columnas": len(columnas)})
    except Exception as e:
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Buscar bajas en BD y generar plantilla salidas ────────────
@router.post("/buscar-bajas")
async def buscar_bajas(
    solicitudes: list[str] = Form(...),
    bd_token:    str        = Form(...),
):
    if bd_token not in _bd_store:
        return JSONResponse({"ok": False, "mensaje": "BD no encontrada — recarga el archivo CSV"})

    bd = _bd_store[bd_token]
    columnas  = bd["columnas"]
    filas_bd  = bd["filas"]

    # Reunir RFC/nombres de los CSV de bajas seleccionados
    rfc_a_sol:    dict[str, str] = {}
    nombre_a_sol: dict[str, str] = {}
    trans_por_sol: dict[str, str] = {}

    for nombre_sol in solicitudes:
        ruta_csv = SOL_DIR / f"{nombre_sol}"
        if not ruta_csv.exists():
            # intentar añadir extensión si viene sin ella
            ruta_csv = SOL_DIR / f"{nombre_sol}.csv" if not nombre_sol.endswith(".csv") else ruta_csv
        if not ruta_csv.exists():
            continue

        num = ruta_csv.stem.replace("-B", "")
        try:
            with open(ruta_csv, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    rfc = (row.get("rfc") or "").upper().strip()
                    nom = (row.get("nombre") or "").upper().strip()
                    t   = (row.get("transporte") or "").strip()
                    if rfc:
                        rfc_a_sol[rfc]    = num
                    if nom:
                        nombre_a_sol[nom] = num
                    if t and num not in trans_por_sol:
                        trans_por_sol[num] = t
        except Exception:
            pass

    # Detectar columnas en la BD
    col_rfc    = _detectar(columnas, ["rfc", "ficha", "curp"])
    col_nombre = _detectar(columnas, ["nombre", "name", "trabajador"])
    col_depto  = _detectar(columnas, ["depto", "departamento", "compania", "empresa"])
    col_cama   = _detectar(columnas, ["cama", "cabina", "cuarto", "habitacion"])

    encontrados = []
    for fila in filas_bd:
        vr = (fila.get(col_rfc)    or "").upper().strip() if col_rfc    else ""
        vn = (fila.get(col_nombre) or "").upper().strip() if col_nombre else ""
        if (vr and vr in rfc_a_sol) or (vn and vn in nombre_a_sol):
            fc = dict(fila)
            sol_num = rfc_a_sol.get(vr) or nombre_a_sol.get(vn, "")
            fc["__solicitud__"]  = sol_num
            fc["__transporte__"] = trans_por_sol.get(sol_num, "")
            encontrados.append(fc)

    if not encontrados:
        return JSONResponse({"ok": False,
                             "mensaje": f"Sin coincidencias — se buscaron {len(rfc_a_sol)} RFC(s)"})

    # Generar xlsx de salidas
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = SOL_DIR / f"_salidas_{ts}.xlsx"

    try:
        n = llenar_plantilla_salidas(
            registros     = encontrados,
            col_nombre    = col_nombre or columnas[0],
            col_depto     = col_depto,
            col_cama      = col_cama,
            col_solicitud = "__solicitud__",
            col_transporte= "__transporte__",
            ruta_destino  = dest,
        )
        return JSONResponse({"ok": True, "encontrados": n, "archivo": dest.name})
    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "mensaje": str(e)})
    except Exception as e:
        logger.error(f"Error generando plantilla salidas: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Generar plantilla de entradas ─────────────────────────────
@router.post("/generar-entradas")
async def generar_entradas(solicitudes: list[str] = Form(...)):
    todos = []
    for nombre in solicitudes:
        ruta = SOL_DIR / f"{nombre}.xlsx"
        if ruta.exists():
            todos.extend(leer_personal_de_xlsx(ruta))

    if not todos:
        return JSONResponse({"ok": False, "mensaje": "No se encontró personal en las solicitudes"})

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = SOL_DIR / f"_entradas_{ts}.xlsx"

    try:
        n = llenar_plantilla_entrada(todos, dest)
        return JSONResponse({"ok": True, "registros": n, "archivo": dest.name})
    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "mensaje": str(e)})
    except Exception as e:
        logger.error(f"Error generando plantilla entradas: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Descargar archivo ─────────────────────────────────────────
@router.get("/descargar/{nombre}")
async def descargar(nombre: str):
    # Buscar en solicitudes/
    ruta = SOL_DIR / nombre
    if not ruta.exists():
        raise HTTPException(404, f"Archivo no encontrado: {nombre}")
    media = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
             if nombre.endswith(".xlsx") else "text/csv")
    return FileResponse(ruta, media_type=media, filename=nombre)


# ── Descargar log ─────────────────────────────────────────────
@router.get("/descargar-log")
async def descargar_log():
    log_file = LOGS_DIR / f"precarga_{datetime.now().strftime('%Y%m%d')}.log"
    if not log_file.exists():
        raise HTTPException(404, "Sin logs disponibles")
    return FileResponse(log_file, media_type="text/plain", filename=log_file.name)


# ── Helper ────────────────────────────────────────────────────
def _detectar(cols: list, candidatos: list) -> Optional[str]:
    for c in candidatos:
        for col in cols:
            if c.lower() in col.lower():
                return col
    return cols[0] if cols else None
