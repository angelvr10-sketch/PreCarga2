"""
core/comandas/repository.py — Lectura y escritura de comandas en Supabase.

Es el UNICO modulo de este conjunto que toca la base de datos. Todo lo demas
(parser, stats, pdf) son funciones puras sobre bytes.

Por que el aislamiento por usuario vive aqui y no en cada endpoint:

    Cada lectura y cada escritura pasa por `clave_de_usuario(usuario)`, que
    normaliza a minusculas. Ningun endpoint acepta el usuario desde el cuerpo de
    la peticion: lo sacan de la cookie con `core.auth.get_current_user`. Si
    alguno lo hiciera, el aislamiento se romperia en silencio y un usuario
    veria las comandas de otro. Por eso la normalizacion es una sola funcion, en
    un solo sitio, en vez de un `.lower()` esparcido por los endpoints.

Que cambia respecto a la app de Streamlit:

  1. Un upsert por LOTES. La app hacia un POST por comanda dentro del loop
     (app.py:549), asi que un reporte de 60 comandas eran 60 viajes a
     PostgREST. Aqui es un solo POST con el array completo.
  2. `fechas_disponibles` no se trae entero. La app hacia
     `select fecha_registro` sin filtro de fecha y se quedaba con el set
     entero en Python (app.py:386), en cada rerun y dos veces (1521 y 1538).
  3. `fecha_registro` se normaliza a ISO antes de guardar o comparar.
"""
from __future__ import annotations

from datetime import date, datetime

from core.comandas.parser import Comanda
from core.comandas.serie import serie_diaria, ventana
from core.supabase_db import HEADERS, BASE, _get, _get_all, _patch, _post, _delete, _count_rows
import httpx

TABLA = "comandas"

# Columnas del upsert, en orden fijo. El insert por lotes de PostgREST exige que
# todas las filas tengan EXACTAMENTE las mismas claves: si una falla con 400,
# es por esto.
COLUMNAS_UPSERT = ("folio", "subido_por", "fecha_registro", "datos", "updated_at")

# PostgREST manda lotes de filas en un solo POST; partirlo evita un payload
# gigante y que un reporte con muchas comandas se caiga por timeout.
TAMANO_LOTE = 200

# Cuantas filas de `fecha_registro` se trae como maximo al buscar fechas, cuando
# la RPC no existe. Es una red de seguridad, no el camino normal.
MAX_FILAS_FECHAS = 2000


class ErrorComandas(Exception):
    """Fallo de la capa de datos de comandas."""


# ── Identidad ──────────────────────────────────────────────────

def clave_de_usuario(usuario: dict) -> str:
    """La clave con la que se guardan y buscan las comandas de este usuario.

    Es `usuarios.username` en minusculas. NUNCA el email: el login de precarga2
    acepta email o username, y `comandas.subido_por` guarda siempre el username
    (es lo que hacia la app de Streamlit).
    """
    username = (usuario.get("username") or "").strip()
    if not username:
        raise ErrorComandas("El usuario de la sesion no tiene username")
    return username.lower()


def _filtro_usuario(username: str, extra: dict | None = None) -> dict:
    """Filtros de PostgREST para las lecturas.

    Usa `ilike` y no `eq` a proposito: hay filas historicas guardadas por la
    app de Streamlit que pueden no estar en minusculas (ella guardaba el valor
    tal cual venía del login). Con `eq` esas filas quedarían invisibles y el
    usuario "perdería" historial.
    """
    filtros = {"subido_por": f"ilike.{username}"}
    if extra:
        filtros.update(extra)
    return filtros


# ── Lectura ────────────────────────────────────────────────────

def _datos_a_comanda(fila: dict) -> Comanda:
    """Convierte una fila de la tabla `comandas` en una Comanda.

    `datos` es un JSONB con el contenido; `folio` esta ademas como columna para
    poder indexar y buscar. Si `datos` viniera nulo, se reconstruye lo que se
    pueda con las columnas sueltas, en vez de perder la fila.

    Fijate en el cache de `_int`: `or defecto` convierte un 0 explicito en 0 y
    tambien trata None como 0, que es lo que se quiere cuando un dato viene
    vacio en el PDF.
    """
    datos = fila.get("datos")
    if not isinstance(datos, dict):
        datos = {
            "comanda": fila.get("folio", ""),
            "horario": fila.get("horario", ""),
            "compania": fila.get("compania", ""),
            "destino": fila.get("destino", ""),
            "pax": fila.get("pax", 0),
            "transporte": fila.get("transporte", ""),
            "menu_1": fila.get("menu_1", 0),
            "menu_2": fila.get("menu_2", 0),
            "tipo": fila.get("tipo", "VIANDA"),
            "observaciones": fila.get("observaciones", ""),
        }

    def _int(clave, defecto=0):
        try:
            return int(datos.get(clave, defecto) or defecto)
        except (TypeError, ValueError):
            return defecto

    return Comanda(
        comanda=str(datos.get("comanda") or fila.get("folio") or ""),
        horario=str(datos.get("horario", "")),
        compania=str(datos.get("compania", "")),
        destino=str(datos.get("destino", "")),
        pax=_int("pax"),
        transporte=str(datos.get("transporte", "")),
        menu_1=_int("menu_1"),
        menu_2=_int("menu_2"),
        tipo=str(datos.get("tipo", "VIANDA")),
        observaciones=str(datos.get("observaciones", "")),
    )


def listar(usuario: dict, fecha_iso: str) -> list[Comanda]:
    """Las comandas de un usuario en una fecha, ordenadas por folio."""
    username = clave_de_usuario(usuario)
    filtros = _filtro_usuario(username, {"fecha_registro": f"eq.{fecha_iso}"})

    filas = _get(TABLA, select="folio,subido_por,fecha_registro,datos", filters=filtros)
    comandas = [_datos_a_comanda(f) for f in filas]
    comandas.sort(key=lambda c: c.comanda)
    return comandas


def obtener(usuario: dict, fecha_iso: str, folio: str) -> Comanda | None:
    """Una comanda concreta, o None si ese usuario no la tiene."""
    username = clave_de_usuario(usuario)
    filtros = _filtro_usuario(
        username, {"fecha_registro": f"eq.{fecha_iso}", "folio": f"eq.{folio}"}
    )
    filas = _get(TABLA, select="folio,subido_por,fecha_registro,datos", filters=filtros)
    if not filas:
        return None
    return _datos_a_comanda(filas[0])


def fechas_disponibles(usuario: dict) -> list[str]:
    """Fechas en las que este usuario tiene comandas, de mas reciente a mas vieja.

    Intenta la RPC `comandas_fechas_usuario(text)`, que hace el DISTINCT en
    Postgres. Si no existe todavia (es una migracion opcional, ver
    migraciones/003_comandas.sql), cae a traer solo la columna de fecha y
    deduplicar aqui, que es mucho mejor que traer la fila entera pero no es
    optimo.
    """
    username = clave_de_usuario(usuario)

    fechas = _fechas_por_rpc(username)
    if fechas is None:
        fechas = _fechas_por_query(username)
    return fechas


def _fechas_por_rpc(username: str) -> list[str] | None:
    """Via RPC. Devuelve None si la RPC no existe, para que se use el otro camino."""
    url = f"{BASE}/rpc/comandas_fechas_usuario"
    try:
        r = httpx.post(url, headers=HEADERS, json={"p_usuario": username}, timeout=20)
    except Exception:
        return None
    if r.status_code != 200:
        return None
    try:
        datos = r.json()
    except Exception:
        return None
    fechas = [str(f.get("fecha_registro")) for f in datos if f.get("fecha_registro")]
    return sorted(set(fechas), reverse=True)


def _fechas_por_query(username: str) -> list[str]:
    """Sin RPC: solo la columna de fecha, ordenada de mas reciente a mas vieja."""
    try:
        filas = _get(
            TABLA,
            select="fecha_registro",
            filters=_filtro_usuario(username),
            order="fecha_registro.desc",
            limit=MAX_FILAS_FECHAS,
        )
    except Exception as exc:
        raise ErrorComandas(f"No se pudieron obtener las fechas: {exc}") from exc

    # El texto es ISO ('YYYY-MM-DD'), asi que el orden lexicografico coincide con
    # el cronologico.
    return sorted({f["fecha_registro"] for f in filas if f.get("fecha_registro")},
                  reverse=True)


def existe(usuario: dict, fecha_iso: str) -> bool:
    """¿Tiene este usuario alguna comanda en esa fecha?"""
    return bool(listar(usuario, fecha_iso))


# ── Lectura GLOBAL (excepcion al aislamiento por usuario) ──────

def serie_diaria_barcos(dias: int, hoy: date | None = None) -> dict:
    """Comandas por dia y por barco en los ultimos `dias` dias, de TODOS los usuarios.

    ── EXCEPCION DELIBERADA AL AISLAMIENTO ──────────────────────────────

    Todas las demas lecturas de este archivo pasan por `clave_de_usuario(usuario)`
    y filtran por el dueño. Esta NO, y es a proposito: alimenta una tarjeta y una
    grafica del DASHBOARD, donde las demas cifras ya son globales (Total
    Solicitudes, Altas, Bajas). Solo devuelve conteos por fecha y por barco, nunca
    el contenido de una comanda ni de quien la subio, asi que no expone datos
    personales: expone la misma agregacion que ya era publica en el dashboard.

    Si alguna vez esta serie se usara para una pantalla por usuario, hay que
    volver a pasar por `clave_de_usuario`. Que quede escrito aqui.

    Trae solo las dos columnas que necesita (`fecha_registro`, `subido_por`) y
    pagina con `_get_all`: `_get` sin `limit` esta capado a 1000 filas por
    PostgREST y trunca en SILENCIO, lo que para una serie temporal seria un
    grafico con dias que de pronto valen cero.
    """
    fechas = ventana(dias, hoy)
    inicio = fechas[0]

    try:
        filas = _get_all(
            TABLA,
            select="fecha_registro,subido_por",
            filters={"fecha_registro": f"gte.{inicio}"},
        )
    except Exception as exc:
        raise ErrorComandas(f"No se pudo obtener la serie de comandas: {exc}") from exc

    return serie_diaria(filas, dias, hoy)


def total_comandas() -> int:
    """Cuantas comandas hay en total, de todos los usuarios. Para la tarjeta del dashboard."""
    try:
        return _count_rows(TABLA)
    except Exception as exc:
        raise ErrorComandas(f"No se pudo contar las comandas: {exc}") from exc


# ── Escritura ──────────────────────────────────────────────────

def _payload(usuario_texto: str, fecha_iso: str, c: Comanda) -> dict:
    """La fila que va a la tabla. Mismo esquema que usaba la app de Streamlit."""
    return {
        "folio": c.comanda,
        "subido_por": usuario_texto,
        "fecha_registro": fecha_iso,
        "datos": c.a_dict(),
        "updated_at": datetime.now().isoformat(),
    }


def upsert_masivo(usuario: dict, fecha_iso: str, comandas: list[Comanda]) -> dict:
    """Guarda todas las comandas de un reporte.

    Un upsert por (folio, subido_por, fecha_registro): volver a subir el mismo
    reporte ACTUALIZA las comandas en vez de duplicarlas ni de borrar las que ya
    estaban. Ese `on_conflict` de tres columnas es lo que impide que el folio
    de un usuario pise el de otro.

    Devuelve {'guardadas': n, 'folios': [...]}.

    IMPORTANTE: si la base de datos no tiene el indice unico de esas tres
    columnas, el upsert falla con 409 y este metodo propaga el error. No se
    degrada a un insert plano a proposito: un insert plano duplicaria folios en
    silencio, que es peor que un error visible. Ver migraciones/003_comandas.sql.
    """
    if not comandas:
        return {"guardadas": 0, "folios": []}

    username = clave_de_usuario(usuario)
    filas = [_payload(username, fecha_iso, c) for c in comandas]

    for c in comandas:
        if set(_payload(username, fecha_iso, c).keys()) != set(COLUMNAS_UPSERT):
            raise ErrorComandas("Las filas del lote no tienen las mismas claves")

    guardadas = 0
    for inicio in range(0, len(filas), TAMANO_LOTE):
        lote = filas[inicio:inicio + TAMANO_LOTE]
        guardadas += len(_upsert_lote(lote))

    return {"guardadas": guardadas, "folios": [c.comanda for c in comandas]}


def _upsert_lote(lote: list[dict]) -> list:
    """Un POST con `resolution=merge-duplicates`, que es el upsert de PostgREST."""
    url = (
        f"{BASE}/{TABLA}"
        "?on_conflict=folio,subido_por,fecha_registro"
    )
    headers = {
        **HEADERS,
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    try:
        r = httpx.post(url, headers=headers, json=lote, timeout=30)
    except Exception as exc:
        raise ErrorComandas(f"No se pudo guardar: {exc}") from exc

    if r.status_code in (200, 201):
        try:
            return r.json() or []
        except Exception:
            return lote

    if r.status_code == 409:
        raise ErrorComandas(
            "La base de datos no tiene el indice unico "
            "(folio, subido_por, fecha_registro) que necesita esta operacion. "
            "Ver migraciones/003_comandas.sql."
        )
    raise ErrorComandas(f"No se pudo guardar (HTTP {r.status_code}): {r.text[:300]}")


def borrar(usuario: dict, fecha_iso: str, folio: str) -> bool:
    """Elimina una comanda. Devuelve False si ese usuario no la tenia."""
    username = clave_de_usuario(usuario)
    filtros = _filtro_usuario(
        username, {"fecha_registro": f"eq.{fecha_iso}", "folio": f"eq.{folio}"}
    )
    try:
        eliminadas = _delete(TABLA, filtros)
    except Exception as exc:
        raise ErrorComandas(f"No se pudo borrar: {exc}") from exc
    return bool(eliminadas)


# ── Soporte ────────────────────────────────────────────────────

def diagnostico(usuario: dict) -> dict:
    """Conteos para el panel de soporte. Solo para admin.

    Es el equivalente al expander "Diagnostico de Datos" de la app de Streamlit
    (app.py:1524-1534).
    """
    username = clave_de_usuario(usuario)

    total_comandas = 0
    total_usuarios = 0
    mis_comandas = 0
    error = None

    try:
        from core.supabase_db import _count_rows

        total_comandas = _count_rows(TABLA)
        total_usuarios = _count_rows(TABLA, {"subido_por": f"ilike.{username}"})
        mis_comandas = total_usuarios
    except Exception as exc:
        error = str(exc)

    fechas = []
    if error is None:
        try:
            fechas = fechas_disponibles(usuario)
        except Exception as exc:
            error = str(exc)

    return {
        "usuario": username,
        "comandas_en_tabla": total_comandas,
        "mis_comandas": mis_comandas,
        "mis_fechas": len(fechas),
        "ultimas_fechas": fechas[:10],
        "error": error,
    }
