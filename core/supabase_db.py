"""core/supabase_db.py — Capa de acceso a Supabase (PostgreSQL)

Reemplaza las bases de datos SQLite (usuarios.db, solicitudes.db)
por llamadas a la API REST de Supabase via httpx.
"""
import os
import time
import urllib.parse
from datetime import datetime
from typing import Optional
from pathlib import Path

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    httpx = None

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")

# ──────────────────────────────────────────────────────────────
#  Seleccion de la clave
# ──────────────────────────────────────────────────────────────
# El backend SIEMPRE usa la service_role key, por dos motivos:
#
#   1. Esta app NO usa Supabase Auth: implementa su propia autenticacion
#      (bcrypt + tabla 'sesiones'), asi que las RLS no aportan nada.
#   2. Con la anon/publishable key el RLS rompe el arranque de dos formas:
#      - bloquea los INSERT  -> PostgREST devuelve 401 con codigo 42501
#        ("new row violates row-level security policy"), un 401 que NO
#        significa token invalido;
#      - filtra los SELECT   -> las tablas devuelven [] en vez de error, asi
#        que init_db cree que el admin no existe e intenta recrearlo.
#
# La service_role key NUNCA debe salir del backend: no se manda al frontend
# y no se usa en URLs publicas (ver get_public_url).
def _elegir_clave() -> tuple[str, str]:
    candidatos = (
        ("service_role", os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")),
        ("service_role", os.getenv("SUPABASE_SERVICE_KEY", "")),
        ("anon", os.getenv("SUPABASE_ANON_KEY", "")),
        ("anon", os.getenv("SUPABASE_KEY", "")),
    )
    for etiqueta, valor in candidatos:
        valor = (valor or "").strip().strip('"').strip("'")
        if valor:
            return valor, etiqueta
    return "", "ninguna"

SUPABASE_KEY, KEY_TIPO = _elegir_clave()

# Headers para las peticiones REST
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

BASE = f"{SUPABASE_URL}/rest/v1"

# Configuramos un timeout más generoso para evitar errores de handshake en redes inestables
TIMEOUT_CONFIG = 30.0
MAX_RETRIES = 3
RETRY_BASE_SEGONDS = 1

# Cliente HTTP persistente (keep-alive). Importado de precarga.
#
# Antes cada llamada usaba `httpx.request(...)`, que crea un Client nuevo por
# peticion: abre TCP, hace el handshake TLS y cierra al terminar. Al procesar
# un PDF eso se paga por CADA persona insertada (ver core.db.guardar_solicitud,
# que hace un _post por fila), asi que un PDF de 60 personas abria 60
# conexiones TLS distintas contra Supabase.
#
# Reutilizar un unico Client mantiene vivos el socket y la sesion TLS, de modo
# que las peticiones siguientes solo pagan el round-trip. httpx.Client es
# thread-safe, lo que importa porque _count_distinct lanza peticiones en
# paralelo con ThreadPoolExecutor.
#
# max_keepalive_connections debe ser >= al numero de peticiones simultaneas
# para que ninguna conexion se descarte entre usos.
_CLIENT = (
    httpx.Client(
        timeout=TIMEOUT_CONFIG,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )
    if HAS_HTTPX
    else None
)


def _reabrir_cliente():
    """Crea el pool de conexiones. Se llama al arrancar y al volver a usarlo
    despues de un `cerrar_cliente()`."""
    global _CLIENT
    if _CLIENT is None and HAS_HTTPX:
        _CLIENT = httpx.Client(
            timeout=TIMEOUT_CONFIG,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _CLIENT


def cerrar_cliente():
    """Cierra el pool de conexiones. Llamar al apagar la app (ver main.py).

    Sin esto, cada recarga de `uvicorn --reload` deja sockets abiertos.

    Dejar `_CLIENT` en None NO deja el modulo inservible: la proxima peticion lo
    reabre (ver `_request_with_retry`). Cerrar es una courtesy con el sistema, no
    un estado terminal.
    """
    global _CLIENT
    if _CLIENT is not None:
        _CLIENT.close()
        _CLIENT = None

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _status_error(response) -> "httpx.HTTPStatusError":
    """Convierte la respuesta en excepcion incluyendo el mensaje de Supabase.

    httpx solo pone "Client error '401 Unauthorized'" en el traceback, pero
    el cuerpo de PostgREST es donde vive la causa real (RLS, columna inexistente,
    violacion de FK...). Sin esto el error de arranque es inaccionable.
    """
    detalle = " ".join(response.text.split())[:500] or "<sin cuerpo>"
    return httpx.HTTPStatusError(
        f"{response.status_code} {response.reason_phrase} | Supabase: {detalle}",
        request=response.request,
        response=response,
    )


def _request_with_retry(method, url, **kwargs):
    """Wrapper para realizar peticiones con reintentos en caso de Timeout o SSL Errors.

    Reintenta errores de transporte y tambien 5xx / 429 de PostgREST. Los 4xx
    no se reintentan: son deterministas y solo gastarian tiempo.
    """
    if not HAS_HTTPX:
        raise RuntimeError("httpx no esta instalado. Ejecuta: pip install httpx")
    if _CLIENT is None:
        # `cerrar_cliente()` dejo el pool cerrado (se llama al apagar la app, y en
        # los tests cuando un TestClient termina). Antes esto era un `raise` con un
        # mensaje que culpaba a httpx, que si estaba instalado: el sintoma era
        # "httpx no esta instalado" siendo que lo que faltaba era reabrir el pool.
        #
        # Con la suite de tests se notaba mucho: el primer test que levanta
        # `TestClient(main.app)` cerraba el pool al salir del `with`, y a partir de
        # ahi cualquier peticion real a Supabase fallaba. En produccion es la
        # misma trampa: cualquier llamada posterior al apagado quedaba muerta
        # hasta reiniciar.
        _reabrir_cliente()

    last_exception = None
    for attempt in range(MAX_RETRIES):
        try:
            # Reutilizamos el cliente persistente: el socket y la sesion TLS
            # se mantienen vivos entre llamadas; el timeout vive en el Client,
            # asi que no hace falta pasarlo en cada peticion.
            response = _CLIENT.request(method, url, **kwargs)

            if response.status_code >= 500 or response.status_code == 429:
                last_exception = _status_error(response)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BASE_SEGONDS * (attempt + 1))
                    continue
                raise last_exception

            if response.status_code >= 400:
                raise _status_error(response)

            return response
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_SEGONDS * (attempt + 1))  # Espera simple

    raise last_exception

# ──────────────────────────────────────────────────────────────
#  Funciones de bajo nivel para llamadas REST
# ──────────────────────────────────────────────────────────────

def _get(table: str, select: str = "*", filters: Optional[dict] = None,
         order: Optional[str] = None, limit: Optional[int] = None) -> list:
    """GET a Supabase table. Devuelve lista de dicts."""
    params = {"select": select}
    if filters:
        for k, v in filters.items():
            params[k] = v
    if order:
        params["order"] = order
    if limit:
        params["limit"] = limit
    
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("GET", url, headers=HEADERS, params=params)
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR GET] Table: {table} | URL: {url} | Params: {params}")
        print(f"Error: {e}")
        raise e

def _get_all(table: str, select: str = "*", filters: Optional[dict] = None,
              order: Optional[str] = None, page_size: int = 1000) -> list:
    """Descarga TODAS las filas paginando, sin sufrir el cap de max-rows.

    `_get` sin `limit` esta sujeto al cap de PostgREST (max-rows = 1000 en este
    proyecto). Si la consulta casa mas filas, la respuesta se TRUNCA en
    silencio: el llamador cree que son todas y no hay ningun error. Por eso
    generar listas de personal con `_get` perderia solicitudes en silencio al
    pasar de 1000 registros; aqui se recorre el total en paginas.
    """
    from core.supabase_db import _count_rows

    total = _count_rows(table, filters)
    if total <= 0:
        return []

    params = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    url = f"{BASE}/{table}"

    filas: list = []
    for inicio in range(0, total, page_size):
        headers = {**HEADERS, "Range": f"{inicio}-{inicio + page_size - 1}"}
        r = _request_with_retry("GET", url, headers=headers, params=params)
        lote = r.json() if r.status_code != 204 else []
        filas.extend(lote)
        if not lote:
            break
    return filas


def _count_rows(table: str, filters: Optional[dict] = None) -> int:
    """Cuenta filas de una tabla Supabase en una sola petición (Prefer: count=exact)."""
    params = {"select": "id"}
    if filters:
        for k, v in filters.items():
            params[k] = v
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry(
            "GET", url,
            headers={**HEADERS, "Prefer": "count=exact", "Range": "0-0"},
            params=params,
        )
        # Content-Range: "0-0/<total>"
        content_range = r.headers.get("content-range", "")
        if "/" in content_range:
            return int(content_range.rsplit("/", 1)[1])
        return len(r.json())
    except Exception as e:
        print(f"\n[DB ERROR COUNT] Table: {table} | Params: {params}")
        print(f"Error: {e}")
        raise e


def _count_distinct(table: str, column: str, filters: Optional[dict] = None) -> int:
    """Cuenta valores distintos no vacíos de una columna.

    Obtiene el total con una sola petición (count=exact) y descarga las
    páginas en paralelo para evitar N peticiones secuenciales lentas.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    params = {"select": column}
    if filters:
        for k, v in filters.items():
            params[k] = v
    url = f"{BASE}/{table}"

    total = _count_rows(table, filters)
    if total <= 0:
        return 0

    page_size = 1000
    starts = list(range(0, total, page_size))

    def _pagina(start: int) -> list:
        headers = {**HEADERS, "Range": f"{start}-{start + page_size - 1}"}
        try:
            r = _request_with_retry("GET", url, headers=headers, params=params)
        except Exception as e:
            print(f"\n[DB ERROR DISTINCT] Table: {table} | URL: {url}")
            print(f"Error: {e}")
            raise e
        return r.json()

    seen: set = set()
    with ThreadPoolExecutor(max_workers=min(8, len(starts))) as ex:
        futures = [ex.submit(_pagina, s) for s in starts]
        for fut in as_completed(futures):
            for row in fut.result():
                v = (row.get(column) or "").strip()
                if v:
                    seen.add(v)
    return len(seen)

def _post(table: str, data: dict) -> Optional[dict]:
    """POST a Supabase table. Devuelve el registro insertado o None."""
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("POST", url, headers=HEADERS, json=data)
        result = r.json()
        return result[0] if result else None
    except Exception as e:
        print(f"\n[DB ERROR POST] Table: {table} | URL: {url} | Data: {data}")
        print(f"Error: {e}")
        raise e

def _post_batch(table: str, data_list: list) -> list:
    """POST de varias filas en UNA sola peticion. Devuelve las filas insertadas.

    PostgREST acepta un array de objetos y los inserta en un unico viaje.
    Antes, guardar_solicitud hacia un _post POR PERSONA: procesar un PDF de
    60 personas eran 60 round-trips a Supabase, que es latencia pura.

    Requisitos que impone el insert batch:
      - todas las filas deben tener las MISMAS claves, si no PostgREST 400;
      - el lote se manda troceado desde core.db para no generar un payload
        gigante (ver POST_BATCH_SIZE).
    """
    if not data_list:
        return []
    keys = set(data_list[0].keys())
    for fila in data_list[1:]:
        if set(fila.keys()) != keys:
            raise ValueError(
                f"Batch inhomogeneo en {table}: se espera {sorted(keys)} "
                f"y se encontro {sorted(fila.keys())}"
            )
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("POST", url, headers=HEADERS, json=data_list)
        return r.json() if r.status_code in (200, 201) else []
    except Exception as e:
        print(f"\n[DB ERROR POST BATCH] Table: {table} | filas={len(data_list)} | Error: {e}")
        raise e

def _delete(table: str, filters: dict) -> list:
    """DELETE de Supabase table. Devuelve los registros eliminados."""
    params = {}
    for k, v in filters.items():
        params[k] = v
    
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("DELETE", url, headers=HEADERS, params=params)
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR DELETE] Table: {table} | URL: {url} | Filters: {filters}")
        print(f"Error: {e}")
        raise e

def _patch(table: str, data: dict, filters: dict) -> list:
    """UPDATE en Supabase table. Devuelve los registros modificados."""
    params = dict(filters)
    url = f"{BASE}/{table}"
    try:
        r = _request_with_retry("PATCH", url, headers=HEADERS, params=params, json=data)
        return r.json() if r.status_code != 204 else []
    except Exception as e:
        print(f"\n[DB ERROR PATCH] Table: {table} | URL: {url} | Data: {data}")
        print(f"Error: {e}")
        raise e

def _exec_sql(sql: str):
    """Ejecuta SQL directo via la API de Supabase (rpc)."""
    pass

def verificar_conexion() -> bool:
    """Verifica que Supabase este accesible y que la clave sirva para LEER.

    Ojo: con la anon/publishable key y RLS activo los SELECT devuelven 200
    con [] (0 filas visibles, no error), asi que un GET 200 NO prueba que la
    clave sirva. Por eso el diagnostico de escritura vive en init_db().
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: falta SUPABASE_URL o la clave de Supabase en .env")
        return False

    try:
        r = _request_with_retry(
            "GET", f"{BASE}/usuarios",
            headers={k: v for k, v in HEADERS.items() if k != "Prefer"},
            params={"select": "id", "limit": 1},
        )
        filas = len(r.json()) if r.status_code == 200 else 0
        if filas == 0:
            print(
                f"AVISO: la clave ({KEY_TIPO}) responde pero la tabla 'usuarios' "
                "devuelve 0 filas. Si esperabas usuarios, casi seguro las RLS "
                "estan filtrandolos: configura SUPABASE_SERVICE_ROLE_KEY."
            )
        return True
    except Exception as e:
        print(f"\n[DB ERROR CONEXION] {e}")
        return False

# ──────────────────────────────────────────────────────────────
#  Gestión de Compañías
# ──────────────────────────────────────────────────────────────

def leer_companias_supabase() -> list:
    """Obtiene todas las compañías desde Supabase."""
    # Retorno de lista de dicts con razon_social y nombre_corto
    return _get("companias")

def agregar_compania_supabase(razon_social: str, nombre_corto: str):
    """Agrega una nueva compañía a Supabase."""
    data = {
        "razon_social": razon_social,
        "nombre_corto": nombre_corto,
        "updated_at": _now()
    }
    return _post("companias", data)

def eliminar_compania_supabase(razon_social: str):
    """Elimina una compañía por su razón social.

    El filtro lleva el operador `eq.` explícito. Sin él, PostgREST lo toma como
    sintaxis (`PGRST100: unexpected "P" expecting "not" or operator`), y el DELETE
    responde 400 con un cuerpo vacío: el borrado NO ocurre y el error no dice por
    qué.

    Esto rompía el botón de borrar de la pantalla de Compañías con CUALQUIER razón
    social: no solo las que empiezan por 'e' o 'i', que es lo que daria el mal
    parseo de una palabra clave, sino todas. `_get` y `_patch` reciben los filtros
    ya con operador desde quien los arma (ver `_filtro_usuario`), así que aquí
    ocurre igual: se pone explícito.
    """
    return _delete("companias", {"razon_social": f"eq.{razon_social}"})

# ──────────────────────────────────────────────────────────────
#  Gestión de Activos
# ──────────────────────────────────────────────────────────────

def leer_activos_supabase() -> list:
    """Obtiene la lista de activos activos."""
    res = _get("activos", select="nombre")
    return [item["nombre"] for item in res]

def agregar_activo_supabase(nombre: str):
    """Agrega un nuevo activo."""
    return _post("activos", {"nombre": nombre})

def eliminar_activo_supabase(nombre: str):
    """Elimina un activo por nombre.

    Mismo `eq.` que en companias: sin el operador, PostgREST responde 400 y no
    borra nada. Los activos son palabras ('ACTIVOS', 'PLATAFORMA...'), asi que el
    fallo es identico.
    """
    return _delete("activos", {"nombre": f"eq.{nombre}"})

# ──────────────────────────────────────────────────────────────
#  Funciones de Storage (Bucket)
# ──────────────────────────────────────────────────────────────

def upload_file_to_storage(bucket_name: str, file_path: Path, file_name: str):
    """Sube un archivo al Storage de Supabase usando PUT para asegurar reemplazo."""
    encoded_file_name = urllib.parse.quote(file_name)
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{encoded_file_name}"
    
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        upload_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/octet-stream"
        }
        
        r = _request_with_retry("PUT", url, headers=upload_headers, content=content)
        return r.json()
    except Exception as e:
        print(f"\n[STORAGE ERROR UPLOAD] File: {file_name} | Error: {e}")
        raise e

def get_public_url(bucket_name: str, file_name: str) -> str:
    """Retorna la URL pública de un archivo en el bucket."""
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket_name}/{file_name}"

def download_file_from_storage(bucket_name: str, file_name: str) -> bytes:
    """Descarga el contenido de un archivo desde Supabase Storage."""
    encoded_file_name = urllib.parse.quote(file_name)
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{encoded_file_name}"
    try:
        r = _request_with_retry("GET", url, headers=HEADERS)
        return r.content
    except Exception as e:
        print(f"\n[STORAGE ERROR DOWNLOAD] File: {file_name} | Error: {e}")
        raise e

def delete_file_from_storage(bucket_name: str, file_name: str):
    """Elimina un archivo del Storage de Supabase."""
    encoded_file_name = urllib.parse.quote(file_name)
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket_name}/{encoded_file_name}"
    try:
        r = _request_with_retry("DELETE", url, headers=HEADERS)
        return r.json()
    except Exception as e:
        print(f"\n[STORAGE ERROR DELETE] File: {file_name} | Error: {e}")
        raise e
