"""core/procesador.py — Lógica de extracción de PDFs y generación de Excel"""
import re
import csv
import copy
import shutil
import openpyxl
import pdfplumber
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from .config import (
    logger, SOL_DIR, RUTA_PLANTILLA, RUTA_PLANTILLA_SALIDA,
    RUTA_PLANTILLA_ENTRADA, RUTA_ACTIVOS, MAPEO_ACTIVOS
)
from .catalogo import obtener_nombre_compania, leer_activos
from .db import (guardar_solicitud, obtener_solicitud, obtener_personal_sube,
                 obtener_personal_baja, normalizar_fecha_iso)
from .supabase_db import _get
from datetime import datetime


# ──────────────────────────────────────────────────────────────
#  Utilidades
# ──────────────────────────────────────────────────────────────

def es_int(valor: str) -> bool:
    try:
        int(valor)
        return True
    except (ValueError, TypeError):
        return False


# ──────────────────────────────────────────────────────────────
#  Excel helpers
# ──────────────────────────────────────────────────────────────

def quitar_celdas_combinadas(hoja) -> None:
    if hoja.merged_cells:
        for rango in list(hoja.merged_cells.ranges):
            hoja.unmerge_cells(str(rango))


def limpiar_celdas(hoja, celda_inicio: str) -> None:
    start_row = hoja[celda_inicio].row
    start_col = hoja[celda_inicio].column
    for row in hoja.iter_rows(
        min_row=start_row, min_col=start_col,
        max_row=hoja.max_row, max_col=hoja.max_column
    ):
        for cell in row:
            cell.value = None


# ──────────────────────────────────────────────────────────────
#  Extracción de PDF
# ──────────────────────────────────────────────────────────────

def extraer_personal_sube(ruta: Path) -> List[Dict]:
    """Extrae filas 1-S del PDF."""
    personal = []
    try:
        with pdfplumber.open(ruta) as pdf:
            numero = 1
            for pagina in pdf.pages:
                for registro in pagina.extract_tables():
                    for celda_original in registro:
                        celda = [x for x in celda_original if x is not None]
                        if re.search(r"- S", str(celda)):
                            personal.append({
                                "id":       numero,
                                "rfc":      celda[1].lstrip("0") if len(celda) > 1 else "",
                                "nombre":   celda[2]             if len(celda) > 2 else "",
                                "libreta":  celda[3][:10]        if len(celda) > 3 else "",
                                "vigencia": celda[4][:10]        if len(celda) > 4 else "",
                                "llegada":  celda[5]             if len(celda) > 5 else "",
                                "salida":   celda[6]             if len(celda) > 6 else "",
                                "dias":     celda[7]             if len(celda) > 7 else "",
                            })
                            numero += 1
        logger.info(f"Extraídos {len(personal)} registros (sube) de {ruta.name}")
    except Exception as e:
        logger.error(f"Error extrayendo personal de {ruta}: {e}")
        raise
    return personal


def extraer_personal_baja(ruta: Path) -> List[Dict]:
    """Extrae filas 1-B del PDF."""
    personal = []
    try:
        with pdfplumber.open(ruta) as pdf:
            numero = 1
            for pagina in pdf.pages:
                for registro in pagina.extract_tables():
                    for celda_original in registro:
                        celda = [x for x in celda_original if x is not None]
                        if re.search(r"- B", str(celda)):
                            personal.append({
                                "id":       numero,
                                "rfc":      celda[1].lstrip("0") if len(celda) > 1 else "",
                                "nombre":   celda[2]             if len(celda) > 2 else "",
                                "libreta":  celda[3][:10]        if len(celda) > 3 else "",
                                "vigencia": celda[4][:10]        if len(celda) > 4 else "",
                                "llegada":  celda[5]             if len(celda) > 5 else "",
                                "salida":   celda[6]             if len(celda) > 6 else "",
                                "dias":     celda[7]             if len(celda) > 7 else "",
                            })
                            numero += 1
    except Exception as e:
        logger.error(f"Error extrayendo bajas de {ruta}: {e}")
    return personal


def extraer_datos_solicitud(ruta: Path) -> Dict:
    """Extrae metadatos del encabezado del PDF."""
    info: Dict = {"nombre_compania": "SIN NOMBRE", "destinohosp": "",
                  "activoA": False, "activoS": False}
    try:
        with pdfplumber.open(ruta) as pdf:
            primera = pdf.pages[0]
            texto   = primera.extract_text()
            lineas  = texto.splitlines()
            tablas  = primera.extract_tables()

            # Número de solicitud
            if lineas:
                partes = lineas[0].split()
                info["solicitud"] = partes[2] if len(partes) > 2 else "SIN_NUM"

            # Contrato (líneas 8-9)
            for li in [8, 9]:
                if li < len(lineas):
                    for palabra in lineas[li].split():
                        if es_int(palabra) and len(palabra) > 8:
                            info["contrato"] = palabra
                            break

            # Destino (RPX, CPZ u otro código tras "HOSP:")
            m_dest = re.search(r"HOSP:\s*([A-Z0-9]+)", texto, re.IGNORECASE)
            info["destinohosp"] = (m_dest.group(1) if m_dest else "").upper()

            # Activos
            cadena = " ".join(lineas[5:7]) if len(lineas) > 6 else ""
            lista_activos = leer_activos()
            a1, a2 = _buscar_activos(cadena, lista_activos)
            info["activoA"] = a1 or False
            info["activoS"] = a2 or False

            # Códigos presupuestales
            for codigo, prefijo in [
                ("elepep", "ELE:"), ("progpre", "PRO:"),
                ("cge", "CGE:"), ("cta", "CTA:"), ("pos", "POS:")
            ]:
                idx = texto.find(prefijo)
                if idx != -1:
                    lng = 16 if codigo in ["elepep", "progpre"] else 8 if codigo != "pos" else 9
                    info[codigo] = texto[idx + 4: idx + 4 + lng]

            # Firmas
            if len(tablas) > 3 and tablas[3]:
                fila0 = tablas[3][0]
                if fila0:
                    ls = (fila0[0] or "").splitlines()
                    info["nombre_solicita"] = ls[1] if len(ls) > 1 else ""
                    info["ficha_solicita"]  = ls[2] if len(ls) > 2 else ""
                if len(fila0) > 1:
                    la = (fila0[1] or "").splitlines()
                    info["nombre_autoriza"] = la[1] if len(la) > 1 else ""
                    info["ficha_autoriza"]  = la[2] if len(la) > 2 else ""

            # Tipo / razón social / transporte
            clave = "Tipo de Personal: Compañía: No. Contrato SAP: Transporte: Itinerario ida: Fec/Hora Itinerario:"
            try:
                idx = lineas.index(clave)
                if idx + 1 < len(lineas):
                    linea_datos = lineas[idx + 1]
                    tokens = linea_datos.split()
                    info["tipo"] = tokens[0] if tokens else ""

                    if info["tipo"] == "PEMEX":
                        info["contrato"]    = "N/A"
                        info["razonsocial"] = "PEMEX"
                    else:
                        contrato_enc = ""
                        for t in tokens[1:]:
                            try:
                                int(t)
                                if len(t) > 8:
                                    contrato_enc = t
                                    break
                            except ValueError:
                                pass
                        if contrato_enc:
                            info["contrato"]    = contrato_enc
                            i = linea_datos.find(contrato_enc)
                            info["razonsocial"] = linea_datos[len(info["tipo"]):i].strip()
                        elif "contrato" in info:
                            i = linea_datos.find(info["contrato"])
                            if i != -1:
                                info["razonsocial"] = linea_datos[len(info["tipo"]):i].strip()
            except ValueError:
                pass

            # Transporte
            for t in ["MEDIOS PROPIOS", "MARITIMO", "AEREO"]:
                for ln in lineas:
                    if t in ln.upper():
                        info["transporte"] = t
                        break
                if "transporte" in info:
                    break

            logger.info(f"Datos extraídos de solicitud {info.get('solicitud','?')}")
    except Exception as e:
        logger.error(f"Error extrayendo datos de {ruta}: {e}")
        raise
    return info


def _buscar_activos(texto: str, lista: List[str]) -> Tuple[Optional[str], Optional[str]]:
    encontrados = []
    for activo in lista:
        inicio = 0
        while True:
            i = texto.find(activo, inicio)
            if i == -1:
                break
            encontrados.append((i, activo))
            inicio = i + len(activo)
    encontrados.sort(key=lambda x: x[0])
    def expandir(a):
        return MAPEO_ACTIVOS.get(a, a) if a else None
    a1 = expandir(encontrados[0][1]) if len(encontrados) >= 1 else None
    a2 = expandir(encontrados[1][1]) if len(encontrados) >= 2 else None
    return a1, a2


# ──────────────────────────────────────────────────────────────
#  Generador de plantilla principal (solicitud → xlsx)
# ──────────────────────────────────────────────────────────────

# A5 dice "Fecha de Solicitud:" y A6 trae =TODAY() en la plantilla, asi que sin
# intervention el documento muestra la fecha en que se abre/imprime, no la de
# arribo del personal.
_CELDA_FECHA_SOLICITUD = "A6"


def _poner_fecha_solicitud(hoja, fecha_llegada: str) -> None:
    """Escribe en A6 ('Fecha de Solicitud') la fecha de LLEGADA del personal.

    Se usa la misma fuente que core.db.guardar_solicitud para la columna
    fecha_llegada (la llegada de la primera persona), de modo que la plantilla
    y la BD no pueden discrepar. Si no hay fecha, se deja la celda como venia
    en vez de escribir un valor inventado.
    """
    if not fecha_llegada:
        return
    # Se normaliza aqui tambien (y no solo en el llamador) para que ninguna
    # fecha dd/mm/yyyy acabe escrita como texto en una celda con formato fecha.
    fecha_llegada = normalizar_fecha_iso(fecha_llegada)
    try:
        hoja[_CELDA_FECHA_SOLICITUD] = datetime.strptime(fecha_llegada, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        # Fecha ilegible: se escribe tal cual para no perderla ni inventar otra.
        hoja[_CELDA_FECHA_SOLICITUD] = fecha_llegada


def _llenar_hoja_plantilla(hoja, info: Dict, personal: List[Dict],
                           personal_baja: List[Dict]) -> List[str]:
    """Llena la hoja activa de la plantilla de solicitud. Devuelve advertencias."""
    quitar_celdas_combinadas(hoja)
    limpiar_celdas(hoja, "A15")

    # Fecha de llegada: la que trae la BD si esta disponible (regenerado desde
    # /api/descargar) y, si no, la del primer personal (PDF nuevo).
    _llegada_1a = personal[0].get("llegada", "") if personal else ""
    _poner_fecha_solicitud(
        hoja,
        normalizar_fecha_iso(info.get("fecha_llegada") or _llegada_1a),
    )

    fila_inicial = 15
    for i, p in enumerate(personal, start=fila_inicial):
        hoja[f"A{i}"] = i - fila_inicial + 1
        hoja[f"C{i}"] = p.get("rfc", "")
        hoja[f"D{i}"] = p.get("nombre", "")
        hoja[f"G{i}"] = p.get("libreta", "")
        hoja[f"H{i}"] = p.get("vigencia", "")
        hoja[f"I{i}"] = p.get("llegada", "")
        hoja[f"J{i}"] = p.get("salida", "")
        hoja[f"K{i}"] = p.get("dias", "")

    fila_firma = len(personal) + fila_inicial + 3
    hoja[f"C{fila_firma}"].value   = info.get("nombre_solicita", "")
    hoja[f"C{fila_firma+1}"].value = info.get("ficha_solicita", "")
    hoja[f"I{fila_firma}"].value   = info.get("nombre_autoriza", "")
    hoja[f"I{fila_firma+1}"].value = info.get("ficha_autoriza", "")

    hoja["A11"].value = info.get("progpre", "")
    hoja["J1"].value  = info.get("solicitud", "")
    hoja["F11"].value = info.get("elepep", "")
    hoja["G11"].value = "PEF"
    hoja["H11"].value = info.get("pos", "")
    hoja["I11"].value = info.get("cge", "")
    hoja["J11"].value = info.get("cta", "")
    hoja["A8"].value  = info.get("tipo", "")
    hoja["G8"].value  = info.get("contrato", "")

    if info.get("razonsocial"):
        hoja["E8"].value = obtener_nombre_compania(info["razonsocial"])

    errores = []
    if info.get("activoA"):
        hoja["E6"].value = info["activoA"]
    else:
        errores.append("Activo solicitante no encontrado")
    if info.get("activoS"):
        hoja["H6"].value = info["activoS"]
    else:
        errores.append("Activo autorizador no encontrado")
    return errores


def llenar_plantilla(ruta_pdf: Path) -> Tuple[bool, str, str]:
    """Procesa un PDF y genera el Excel de solicitud.

    Devuelve (exito, mensaje, folio). El folio es el numero de solicitud
    ("" si fallo) y es lo que el frontend necesita para descargar el xlsx
    recien generado via /api/descargar/{folio}.xlsx, que lo regenera desde la BD.
    """
    try:
        if not RUTA_PLANTILLA.exists():
            return False, f"Plantilla no encontrada: {RUTA_PLANTILLA}", ""
        if not ruta_pdf.exists():
            return False, f"PDF no encontrado: {ruta_pdf}", ""

        personal = extraer_personal_sube(ruta_pdf)
        info     = extraer_datos_solicitud(ruta_pdf)

        if not personal:
            return False, "No se encontró personal en el PDF", ""

        personal_baja = extraer_personal_baja(ruta_pdf)

        wb   = openpyxl.load_workbook(RUTA_PLANTILLA)
        hoja = wb.active

        errores = _llenar_hoja_plantilla(hoja, info, personal, personal_baja)

        nombre_salida = f"{info.get('solicitud', 'SIN_NUM')}.xlsx"
        folio = nombre_salida[:-5]  # sin la extension
        ruta_salida   = SOL_DIR / nombre_salida
        wb.save(ruta_salida)

        # Guardar metadatos en la BD para listado rápido
        compania_corta = obtener_nombre_compania(info.get("razonsocial", "")) \
                         if "razonsocial" in info else ""
        info["compania_corta"] = compania_corta
        guardar_solicitud(info, personal, personal_baja, nombre_salida)

        mensaje = f"Archivo generado: {nombre_salida}"
        if personal_baja:
            mensaje += f" | Bajas: {len(personal_baja)} persona(s)"
        if errores:
            mensaje += f" | Advertencias: {', '.join(errores)}"

        logger.info(mensaje)
        return True, mensaje, folio

    except Exception as e:
        msg = f"Error procesando {ruta_pdf.name}: {e}"
        logger.error(msg)
        return False, msg, ""


def generar_plantilla_desde_bd(numero: str) -> Optional[io.BytesIO]:
    """Regenera el xlsx de una solicitud usando SOLO datos de la BD.
    Devuelve el archivo en memoria, o None si no hay plantilla/personal."""
    try:
        if not RUTA_PLANTILLA.exists():
            return None

        sol = obtener_solicitud(numero)
        if not sol:
            return None

        info = {
            "solicitud": sol.get("numero", numero),
            "compania": sol.get("compania", ""),
            "compania_corta": sol.get("compania", ""),
            "razonsocial": sol.get("razonsocial") or sol.get("compania", ""),
            "transporte": sol.get("transporte", ""),
            "tipo": sol.get("tipo", ""),
            "contrato": sol.get("contrato", ""),
            "activoA": sol.get("activo_a") or "",
            "activoS": sol.get("activo_s") or "",
            "destinohosp": sol.get("destinohosp") or "",
            "elepep": sol.get("elepep") or "",
            "progpre": sol.get("progpre") or "",
            "cge": sol.get("cge") or "",
            "cta": sol.get("cta") or "",
            "pos": sol.get("pos") or "",
            "nombre_solicita": sol.get("nombre_solicita") or "",
            "ficha_solicita": sol.get("ficha_solicita") or "",
            "nombre_autoriza": sol.get("nombre_autoriza") or "",
            "ficha_autoriza": sol.get("ficha_autoriza") or "",
            # Alimenta A6 ("Fecha de Solicitud"), que en la plantilla venia
            # como =TODAY(). Ver _poner_fecha_solicitud.
            "fecha_llegada": sol.get("fecha_llegada") or "",
        }

        personal = obtener_personal_sube(numero)
        if not personal:
            return None
        personal_baja = obtener_personal_baja(numero) if (sol.get("tiene_bajas") or sol.get("n_bajas")) else []

        wb   = openpyxl.load_workbook(RUTA_PLANTILLA)
        hoja = wb.active
        _llenar_hoja_plantilla(hoja, info, personal, personal_baja)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Error regenerando plantilla desde BD para {numero}: {e}")
        return None


def listar_solicitudes_xlsx(page: int = 1, limit: int = 20, search: Optional[str] = None) -> tuple[list[dict], int]:
    """
    Lee solicitudes desde Supabase con paginación y búsqueda opcional.
    Devuelve una tupla: (lista de dicts, total_de_registros).
    """
    from .supabase_db import _get, _count_rows
    
    try:
        offset = (page - 1) * limit
        
        # Construir filtros
        filters = {}
        if search:
            # Supabase usa 'ilike' para búsqueda parcial insensible a mayúsculas
            filters["numero"] = f"ilike.%{search.strip()}%"
        
        # 1. Obtener los registros paginados
        params = {
            "select": "*", 
            "order": "fecha_llegada.desc,procesado.desc", 
            "limit": limit, 
            "offset": offset
        }
        
        # Combinar filtros y parámetros
        query_params = {**params}
        if filters:
            query_params.update(filters)
            
        rows = _get("solicitudes", filters=query_params)
        
        # 2. Obtener el total de registros para calcular las páginas
        # Si hay búsqueda, el total debe reflejar solo los resultados filtrados
        total_filters = {"numero": f"ilike.%{search.strip()}%"} if search else None
        total_count = _count_rows("solicitudes", total_filters)

        result = []
        for r in rows:
            fecha_mod = "" 
            
            result.append({
                "id":          r["id"],
                "nombre":      r["numero"],
                "compania":    r["compania"] or "",
                "n":           r["n_personas"],
                "fecha":       r["fecha_llegada"] or "",
                "fecha_mod":   fecha_mod,
                "procesado":   r.get("procesado") or "",
                "tipo":        r.get("tipo") or "",
                "archivo":     r.get("archivo") or "",
                "tiene_bajas": bool(r["tiene_bajas"]),
                "n_bajas":     r["n_bajas"],
                "destino":     r.get("destinohosp") or "",
            })
        return result, total_count
    except Exception as e:
        logger.error(f"Error en listar_solicitudes_xlsx: {e}")
        return [], 0


def leer_meta_xlsx(ruta: Path) -> dict:
    """Fallback: abre el xlsx directamente. Solo se usa para archivos
    que aún no tienen registro en la BD (solicitudes antiguas)."""
    meta = {"compania": "", "n": 0, "fecha": ""}
    try:
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        ws = wb.active
        meta["compania"] = str(ws["E8"].value or "").strip()
        n = 0
        fecha = ""
        for row in ws.iter_rows(min_row=15, max_row=ws.max_row,
                                min_col=4, max_col=9, values_only=True):
            if not row[0] or not str(row[0]).strip():
                break
            n += 1
            if not fecha and row[5]:
                fecha = str(row[5]).split(" ")[0][:10]
        meta["n"]     = n
        meta["fecha"] = fecha
        wb.close()
    except Exception:
        pass
    return meta


# ──────────────────────────────────────────────────────────────
#  Plantilla de salidas (bajas)
# ──────────────────────────────────────────────────────────────

_BLOQUE_TAMANO     = 15
_FILA_DATOS_INICIO = 23
_CELDA_FECHA       = "C18"

# Texto que va en A12 (destino) según el destino de la solicitud
_DESTINO_A12 = {
    "RPX": "REFORMA PEMEX",
    "CPZ": 'U.H.F "CERRO DE LA PEZ"',
}


def _dividir_bloques(registros: list) -> list:
    """Divide registros en bloques de a 15 (una hoja por bloque)."""
    return [registros[i:i + _BLOQUE_TAMANO]
            for i in range(0, len(registros), _BLOQUE_TAMANO)]


def _copiar_imagenes(ws_origen, ws_destino):
    """Copia todas las imágenes de una hoja a otra preservando su posición."""
    for img in ws_origen._images:
        nueva_img = copy.deepcopy(img)
        ws_destino.add_image(nueva_img)


def _hojas_por_bloque(wb, hoja_base, total: int) -> list:
    """Crea tantas hojas como bloques de 15 hagan falta, copiando la plantilla."""
    prefix = hoja_base.title.strip()
    hojas = []
    for b in range((total + _BLOQUE_TAMANO - 1) // _BLOQUE_TAMANO):
        inicio = b * _BLOQUE_TAMANO + 1
        fin    = min((b + 1) * _BLOQUE_TAMANO, total)
        nombre = f"{prefix}({inicio}-{fin})"
        if b == 0:
            hoja_base.title = nombre
            hojas.append(hoja_base)
        else:
            nueva = wb.copy_worksheet(hoja_base)
            nueva.title = nombre
            _copiar_imagenes(hoja_base, nueva)
            hojas.append(nueva)
    return hojas


def _informacion_solicitud(numero, cache: dict) -> dict:
    """Devuelve la solicitud (con cache) o un dict vacío."""
    sn = str(numero or "").strip()
    if not sn:
        return {}
    if sn not in cache:
        cache[sn] = obtener_solicitud(sn) or {}
    return cache[sn]


def _precargar_solicitudes(cache: dict, numeros) -> None:
    """Carga en una sola llamada (in.) las solicitudes que faltan en el cache."""
    pendientes = []
    vistos = set()
    for n in numeros:
        sn = str(n or "").strip()
        if sn and sn not in cache and sn not in vistos:
            vistos.add(sn)
            pendientes.append(sn)
    if not pendientes:
        return
    filas = _get("solicitudes", filters={"numero": f"in.({','.join(pendientes)})"})
    encontradas = {str(r.get("numero") or ""): r for r in filas}
    for sn in pendientes:
        cache[sn] = encontradas.get(sn, {})


def _fecha_arribo(bloque: list, key_sol: str, cache: dict) -> str:
    """Fecha de arribo (fecha_llegada) más temprana entre los registros del bloque."""
    fechas = []
    for reg in bloque:
        sol = _informacion_solicitud(reg.get(key_sol), cache)
        f = (sol.get("fecha_llegada") or "").strip()
        if f:
            fechas.append(f)
    return min(fechas) if fechas else ""


def _destino_por_bloque(bloque: list, key_sol: str, cache: dict) -> str:
    """Destino (destinohosp) del bloque: CPZ tiene prioridad, luego RPX, sino el primero."""
    destinos = []
    for reg in bloque:
        sol = _informacion_solicitud(reg.get(key_sol), cache)
        d = (sol.get("destinohosp") or "").strip().upper()
        if d and d not in destinos:
            destinos.append(d)
    if "CPZ" in destinos:
        return "CPZ"
    if "RPX" in destinos:
        return "RPX"
    return destinos[0] if destinos else ""


def _poner_fecha(ws, fecha_llegada: str) -> None:
    """Escribe la fecha de arribo en C18 (celda FECHA de la plantilla)."""
    if not fecha_llegada:
        return
    try:
        ws[_CELDA_FECHA] = datetime.strptime(fecha_llegada, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        ws[_CELDA_FECHA] = fecha_llegada


def llenar_plantilla_salidas(registros: List[Dict], col_nombre: str,
                              col_depto: Optional[str], col_cama: Optional[str],
                              col_solicitud: Optional[str], col_transporte: Optional[str],
                              ruta_destino: Path, destinohosp: str = "") -> int:
    if not RUTA_PLANTILLA_SALIDA.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {RUTA_PLANTILLA_SALIDA}")
    if not registros:
        return 0
    registros = sorted(registros, key=lambda f: (
        (f.get(col_depto)  or "").upper(),
        (f.get(col_nombre) or "").upper(),
    ))
    shutil.copy2(RUTA_PLANTILLA_SALIDA, ruta_destino)
    wb = openpyxl.load_workbook(ruta_destino)
    ws_base = wb["SALIDAS"]

    bloques = _dividir_bloques(registros)
    hojas   = _hojas_por_bloque(wb, ws_base, len(registros))
    cache   = {}
    _precargar_solicitudes(cache, (f.get(col_solicitud) for f in registros))

    for hoja, bloque in zip(hojas, bloques):
        hoja[_CELDA_FECHA] = "=TODAY()"
        dest = _destino_por_bloque(bloque, col_solicitud, cache) or (destinohosp or "").upper()
        texto_destino = _DESTINO_A12.get(dest)
        if texto_destino:
            hoja["A12"] = texto_destino
        for j, fila in enumerate(bloque):
            r = _FILA_DATOS_INICIO + j
            hoja.cell(r, 3).value  = (fila.get(col_nombre)     or "").strip()
            hoja.cell(r, 4).value  = (fila.get(col_depto)      or "").strip() if col_depto     else ""
            hoja.cell(r, 6).value  = (fila.get(col_solicitud)  or "").strip() if col_solicitud else ""
            hoja.cell(r, 7).value  = (fila.get(col_cama)       or "").strip() if col_cama      else ""
            hoja.cell(r, 8).value  = (fila.get(col_transporte) or "").strip() if col_transporte else ""

    wb.save(ruta_destino)
    return len(registros)


# ──────────────────────────────────────────────────────────────
#  Plantilla de entradas (altas)
# ──────────────────────────────────────────────────────────────

def leer_personal_de_xlsx(source: Union[Path, io.BytesIO]) -> List[Dict]:
    personal = []
    try:
        # Carga el libro desde el archivo o el stream de bytes
        wb = openpyxl.load_workbook(source, data_only=True)
        ws = wb.active
        compania   = str(ws["E8"].value or "").strip()
        transporte = ""
        for col in range(7, 12):
            v = str(ws.cell(8, col).value or "")
            for t in ["MEDIOS PROPIOS", "MARITIMO", "AEREO"]:
                if t in v.upper():
                    transporte = t
                    break
            if transporte:
                break
        
        # El numero de solicitud está en la celda J1
        num_sol = str(ws["J1"].value or "").strip()
        if not num_sol:
            # Si es un archivo Path, usamos el nombre sin extensión. Si es BytesIO, usamos un valor genérico o el esperado.
            num_sol = source.stem if isinstance(source, Path) else "MEM_FILE"

        for row in ws.iter_rows(min_row=15, max_row=ws.max_row):
            id_val = row[0].value
            if id_val is None:
                break
            try:
                int(str(id_val).strip())
            except ValueError:
                break
            rfc    = str(row[2].value or "").strip()
            nombre = str(row[3].value or "").strip()
            if not nombre and not rfc:
                break
            personal.append({"nombre": nombre, "rfc": rfc,
                              "compania": compania, "solicitud": num_sol,
                              "transporte": transporte})
    except Exception as e:
        name = source.name if isinstance(source, Path) else "BytesStream"
        logger.error(f"Error leyendo {name}: {e}")
    return personal


def llenar_plantilla_entrada(registros: List[Dict], ruta_destino: Path) -> int:
    if not RUTA_PLANTILLA_ENTRADA.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {RUTA_PLANTILLA_ENTRADA}")
    if not registros:
        return 0
    registros = sorted(registros, key=lambda r: (
        (r.get("compania") or "").upper(),
        (r.get("nombre")   or "").upper(),
    ))
    shutil.copy2(RUTA_PLANTILLA_ENTRADA, ruta_destino)
    wb = openpyxl.load_workbook(ruta_destino)
    ws_base = next((ws for ws in wb.worksheets if "ENTRAD" in ws.title.upper()),
                   wb.worksheets[0])

    bloques = _dividir_bloques(registros)
    hojas   = _hojas_por_bloque(wb, ws_base, len(registros))
    cache   = {}
    _precargar_solicitudes(cache, (r.get("solicitud") for r in registros))

    for hoja, bloque in zip(hojas, bloques):
        _poner_fecha(hoja, _fecha_arribo(bloque, "solicitud", cache))
        texto_destino = _DESTINO_A12.get(_destino_por_bloque(bloque, "solicitud", cache))
        if texto_destino:
            hoja["A12"] = texto_destino
        for j, reg in enumerate(bloque):
            f = _FILA_DATOS_INICIO + j
            hoja.cell(f, 3).value  = reg.get("nombre",     "")
            hoja.cell(f, 4).value  = ""
            hoja.cell(f, 5).value  = reg.get("rfc",        "")
            hoja.cell(f, 6).value  = reg.get("compania",   "")
            hoja.cell(f, 7).value  = ""
            hoja.cell(f, 8).value  = reg.get("solicitud",  "")
            hoja.cell(f, 9).value  = ""
            hoja.cell(f, 10).value = reg.get("transporte", "")

    wb.save(ruta_destino)
    return len(registros)
