"""routers/api.py — Endpoints de acción: upload, procesamiento, descarga"""
import csv
import io
import uuid
import tempfile
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, RedirectResponse

from core import (
    llenar_plantilla, leer_personal_de_xlsx,
    llenar_plantilla_entrada, llenar_plantilla_salidas,
    logger, SOL_DIR, LOGS_DIR,
)
from core.config import RUTA_PLANTILLA_SALIDA, RUTA_PLANTILLA_ENTRADA
from core.auth import get_current_user, puede_descargar, contar_descarga, MAX_DESCARGAS_GRATIS
from core.db import obtener_personal_baja_db
from core.supabase_db import upload_file_to_storage, download_file_from_storage, delete_file_from_storage

router = APIRouter(prefix="/api")

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
        
        if exito:
            # Buscar el archivo generado más reciente en SOL_DIR
            archivos = sorted(SOL_DIR.glob("*.xlsx"), key=os.path.getmtime, reverse=True)
            if archivos:
                archivo_gen = archivos[0]
                upload_file_to_storage("solicitudes", archivo_gen, archivo_gen.name)
                archivo_gen.unlink()
                
        return JSONResponse({"ok": exito, "mensaje": mensaje})

    except Exception as e:
        logger.error(f"Error en /api/procesar-pdf: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Util: detectar delimitador de CSV ──────────────────────────
def _detect_delimiter(sample: str) -> str:
    common = {',', '\t', ';', '|'}
    counts = {}
    for d in common:
        counts[d] = sample.count(d)
    return max(counts, key=counts.get)  # type: ignore[arg-type]


# ── Cargar BD de personal ─────────────────────────────────────
@router.post("/cargar-bd")
async def cargar_bd(file: UploadFile = File(...)):
    try:
        contenido = await file.read()

        # Si es XLSX, convertirlo a CSV
        if contenido[:4] == b"PK\x03\x04":
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
            ws = wb.active
            filas = list(ws.iter_rows(values_only=True))
            if not filas:
                return JSONResponse({"ok": False, "mensaje": "El XLSX está vacío"})
            with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as tmp:
                w = csv.writer(tmp, delimiter="\t")
                for f in filas:
                    w.writerow(f)
                tmp_path = Path(tmp.name)
            delim = "\t"
            n_columnas = len(filas[0]) if filas else 0
        else:
            texto = contenido.decode("utf-8", errors="replace")
            delim = _detect_delimiter(texto.split("\n")[0]) if texto.split("\n")[0] else ","
            n_columnas = len(texto.split("\n")[0].split(delim)) if texto.split("\n")[0] else 0
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                tmp.write(contenido)
                tmp_path = Path(tmp.name)

        token = str(uuid.uuid4())
        upload_file_to_storage("solicitudes", tmp_path, f"bd_{token}.csv")
        tmp_path.unlink()
        return JSONResponse({"ok": True, "token": token, "columnas": n_columnas, "delim": delim})
    except Exception as e:
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Buscar bajas en BD y generar plantilla salidas ────────────
@router.post("/buscar-bajas")
async def buscar_bajas(
    request: Request,
    solicitudes: list[str] = Form(...),
    bd_token:    str        = Form(...),
):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"ok": False, "mensaje": "No autorizado"}, status_code=401)

    # Descargar BD desde Storage
    try:
        content = download_file_from_storage("solicitudes", f"bd_{bd_token}.csv")
    except Exception:
        return JSONResponse({"ok": False, "mensaje": "BD no encontrada — recarga el archivo CSV"})

    sample = content.decode("utf-8", errors="replace")[:4096]
    delim = _detect_delimiter(sample)
    reader = csv.DictReader(io.TextIOWrapper(io.BytesIO(content), encoding="utf-8", newline="", errors="replace"), delimiter=delim)
    columnas = list(reader.fieldnames or [])
    filas_bd = list(reader)

    # Limpiar BD de Storage
    try:
        delete_file_from_storage("solicitudes", f"bd_{bd_token}.csv")
    except Exception:
        pass

    # Reunir RFC/nombres desde Supabase (con fallback a CSV legacy)
    rfc_a_sol:    dict[str, str] = {}
    nombre_a_sol: dict[str, str] = {}
    trans_por_sol: dict[str, str] = {}

    for nombre_sol in solicitudes:
        num = nombre_sol.replace("-B", "") if nombre_sol.endswith("-B") else nombre_sol
        personal_baja = obtener_personal_baja_db(num)

        if not personal_baja:
            # Fallback: leer CSV para solicitudes pre-migración
            ruta_csv = SOL_DIR / f"{num}-B.csv"
            if ruta_csv.exists():
                try:
                    with open(ruta_csv, newline="", encoding="utf-8") as f:
                        for row in csv.DictReader(f):
                            rfc = (row.get("rfc") or "").upper().strip()
                            nom = (row.get("nombre") or "").upper().strip()
                            t   = (row.get("transporte") or "").strip()
                            if rfc: rfc_a_sol[rfc] = num
                            if nom: nombre_a_sol[nom] = num
                            if t and num not in trans_por_sol: trans_por_sol[num] = t
                except Exception:
                    pass
            continue

        for p in personal_baja:
            rfc = (p.get("rfc") or "").upper().strip()
            nom = (p.get("nombre") or "").upper().strip()
            t   = (p.get("transporte") or "").strip()
            if rfc: rfc_a_sol[rfc] = num
            if nom: nombre_a_sol[nom] = num
            if t and num not in trans_por_sol: trans_por_sol[num] = t

    col_rfc       = _detectar(columnas, ["rfc", "ficha", "curp"])
    col_nombre    = _detectar(columnas, ["nombre", "name", "trabajador"])
    col_depto     = _detectar(columnas, ["depto", "departamento", "compania", "empresa"])
    col_cama      = _detectar(columnas, ["cama", "cabina", "cuarto", "habitacion"])
    col_sol_csv   = _detectar(columnas, ["solicitud"])

    encontrados = []
    for fila in filas_bd:
        vr = (fila.get(col_rfc)    or "").upper().strip() if col_rfc    else ""
        vn = (fila.get(col_nombre) or "").upper().strip() if col_nombre else ""
        if (vr and vr in rfc_a_sol) or (vn and vn in nombre_a_sol):
            fc = dict(fila)
            sol_num = rfc_a_sol.get(vr) or nombre_a_sol.get(vn, "")
            fc["__solicitud__"]  = (fila.get(col_sol_csv) or "").strip() if col_sol_csv else sol_num
            fc["__transporte__"] = trans_por_sol.get(sol_num, "")
            encontrados.append(fc)

    if not encontrados:
        return JSONResponse({"ok": False, "mensaje": f"Sin coincidencias — se buscaron {len(rfc_a_sol)} RFC(s)"})

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
        upload_file_to_storage("solicitudes", dest, dest.name)
        dest.unlink()
        return JSONResponse({"ok": True, "encontrados": n, "archivo": dest.name})
    except Exception as e:
        logger.error(f"Error generando plantilla salidas: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Generar plantilla de entradas ─────────────────────────────
@router.post("/generar-entradas")
async def generar_entradas(solicitudes: list[str] = Form(...)):
    todos = []
    
    def sync_process(nombre):
        nombre_archivo = f"{nombre}.xlsx"
        try:
            contenido = download_file_from_storage("solicitudes", nombre_archivo)
            return leer_personal_de_xlsx(io.BytesIO(contenido))
        except Exception as e:
            logger.error(f"Error procesando {nombre_archivo}: {e}")
            return []

    # Ejecutamos las descargas en hilos para no bloquear el event loop y ganar velocidad
    resultados = await asyncio.gather(*[asyncio.to_thread(sync_process, n) for n in solicitudes])
    
    for res in resultados:
        todos.extend(res)

    if not todos:
        return JSONResponse({"ok": False, "mensaje": "No se encontró personal en las solicitudes seleccionadas en el almacenamiento"})

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = SOL_DIR / f"_entradas_{ts}.xlsx"

    try:
        n = llenar_plantilla_entrada(todos, dest)
        upload_file_to_storage("solicitudes", dest, dest.name)
        dest.unlink()
        return JSONResponse({"ok": True, "registros": n, "archivo": dest.name, "download_url": f"/api/descargar/{dest.name}"})
    except Exception as e:
        logger.error(f"Error generando plantilla entradas: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)})


# ── Descargar archivo ─────────────────────────────────────────
@router.get("/descargar/{nombre}")
async def descargar(request: Request, nombre: str):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    puede, razon = puede_descargar(user)
    if not puede:
        return RedirectResponse("/checkout?no_downloads=1", status_code=303)

    from core.auth import suscripcion_vigente
    if suscripcion_vigente(user):
        contar_descarga(user["id"])

    try:
        # Ahora bajamos el archivo desde Supabase Storage en lugar del disco local
        content = download_file_from_storage("solicitudes", nombre)
        
        # Una vez descargado el contenido, eliminamos el archivo del bucket 
        # para no conservar las listas temporales generadas
        try:
            delete_file_from_storage("solicitudes", nombre)
        except Exception as e:
            logger.error(f"Error eliminando archivo temporal {nombre} tras descarga: {e}")

        media = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                 if nombre.endswith(".xlsx") else "text/csv")
        
        return StreamingResponse(
            io.BytesIO(content), 
            media_type=media, 
            headers={"Content-Disposition": f"attachment; filename={nombre}"}
        )
    except Exception as e:
        logger.error(f"Error descargando archivo {nombre} desde storage: {e}")
        raise HTTPException(404, f"Archivo no encontrado en el storage: {nombre}")


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
