"""
core/catalogo.py — Consultas de companias y activos.

── DE DONDE VIENE AHORA ────────────────────────────────────────────────

Antes estas funciones leian `lib/companias.csv` y `lib/activos.csv`, mientras
que la UI (pantalla de Companias y de Activos) escribia en Supabase. Eran DOS
almacenes distintos y nadie los sincronizaba, asi que cualquier alta hecha desde
la app era invisible para el procesador:

    IXT-06102026-0278  razonsocial = 'MICOPERI DE MEXICO SA DE CV'
                       alias en Supabase: MICOPERI   <- lo habia agregado el usuario
                       lo que ponia en el Excel: 'MICOPERI DE MEXICO SA DE CV'

El alias existe en la tabla `companias` pero `obtener_nombre_compania` nunca la
miro. Lo mismo con activos: un activo agregado desde la UI no lo encontraba
`_buscar_activos`, y la solicitud salia con el aviso "Activo solicitante no
encontrado".

Decision del 2026-10-07: **Supabase es la unica fuente de verdad.** El CSV se deja
de usar. Motivo aparte del bug: en produccion el disco es efimo (Fly.io), asi que
un CSV escrito en caliente se pierde en el siguiente reinicio. Un catalogo que
solo sobrevive si redespliegas no es un catalogo.

── LA CACHE ─────────────────────────────────────────────────────────────

Cada PDF procesado consultaba el CSV una vez por hoja, y `_buscar_activos` la
volvia a leer por PDF. Traducido a peticiones HTTP eso es un request a Supabase
por cada archivo. Se cachea en memoria:

    CATALOGO_TTL_SEGUNDOS = 300

Cinco minutos es el margen justo para que el procesador no vaya a la base en cada
PDF y para que un alta desde la UI se vea casi de inmediato. Quien necesite el
cambio al instante (un PDF justo despues de agregar la compania) puede llamar a
`invalidar_cache()`; el endpoint de alta lo hace solo.

Con dos workers (uvicorn --workers 2) hay dos caches, una por proceso. No es
inconsistencia: cada una refresca sola en 5 minutos y ambas parten del mismo
estado de Supabase.
"""
from __future__ import annotations

import logging
import threading
import time

from core.supabase_db import (
    leer_activos_supabase,
    leer_companias_supabase,
)

logger = logging.getLogger(__name__)

# Marginalia de la cache en segundos.
CATALOGO_TTL_SEGUNDOS = 300


class _Cache:
    """Un valor con caducidad, protegido contra lecturas simultaneas.

    `threading.Lock` porque con `--workers 2` y varios hilos por worker pueden
    entrar a la vez al primer PDF. Sin el candado, dos hilos piden el catalogo a
    Supabase a la vez y se-wastean una peticion.
    """

    def __init__(self, ttl: float):
        self._ttl = ttl
        self._lock = threading.Lock()
        self._valor = None
        self._vence_en = 0.0

    def obtener(self, calcular) -> object:
        ahora = time.monotonic()
        if self._valor is not None and ahora < self._vence_en:
            return self._valor
        with self._lock:
            # Otro hilo pudo haberlo calculado mientras se esperaba el candado.
            ahora = time.monotonic()
            if self._valor is not None and ahora < self._vence_en:
                return self._valor
            self._valor = calcular()
            self._vence_en = ahora + self._ttl
            return self._valor

    def invalidar(self) -> None:
        with self._lock:
            self._valor = None
            self._vence_en = 0.0


_cache_companias = _Cache(CATALOGO_TTL_SEGUNDOS)
_cache_activos = _Cache(CATALOGO_TTL_SEGUNDOS)

# Indice razon_social normalizada -> alias, para no recorrer 35 filas por PDF.
_indice_companias: dict[str, str] = {}

# Alias normalizados que existen en el catalogo. Sirve para distinguir "esta fila ya
# venia abreviada" de "esta fila trae un nombre que no conozco".
_alias_companias: set[str] = set()


def _normalizar(texto: str | None) -> str:
    """Minúsculas, sin espacios sobrantes.

    La comparación es EXACTA y sin tildes a proposito. Las razones sociales vienen
    de OCR y de captura manual: la misma compañía aparece con y sin 'S.A. DE
    C.V.', con y sin acentos. Ajustar eso por heurística (buscar el prefijo más
    largo) adivina, y un alias equivocado en un documento firmado es peor que no
    tener alias. Si hace falta, se agrega la variante exacta como fila propia.
    """
    return (texto or "").strip().lower()


# ── Compañías ──────────────────────────────────────────────────

def _cargar_companias() -> dict[str, str]:
    global _indice_companias, _alias_companias
    filas = leer_companias_supabase()
    indice: dict[str, str] = {}
    alias_vistos: set[str] = set()
    for c in filas:
        razon = _normalizar(c.get("razon_social"))
        if not razon:
            continue
        alias = c.get("nombre_corto") or ""
        indice[razon] = alias.strip() or c.get("razon_social", "").strip()
        alias_vistos.add(_normalizar(indice[razon]))
    _indice_companias = indice
    _alias_companias = alias_vistos
    return indice


def indice_companias() -> dict[str, str]:
    """Diccionario `{razon_social normalizada: alias}`. Cacheado."""
    return _cache_companias.obtener(_cargar_companias)  # type: ignore[return-value]


def obtener_nombre_compania(razon_social: str) -> str:
    """El alias de esta razón social, o la razón social misma si no hay alias.

    Si la razón social no esta en la tabla, se devuelve tal cual: el documento se
    genera igual, solo sin abreviar. Fallar aqui dejaria al usuario sin Excel, que
    es peor que un nombre largo en la celda E8.
    """
    return indice_companias().get(_normalizar(razon_social), (razon_social or "").strip())


def nombre_para_listado(fila: dict) -> str:
    """El nombre de compañía que debe verse en los LISTADOS (dashboard, Altas, Bajas).

    ── POR QUÉ NO BASTA CON LEER `compania` ───────────────────────────────

    La columna `solicitudes.comania` guarda el alias que se resolvió AL PROCESAR EL
    PDF: es una foto del catálogo de ese momento. Se reportó que en los listados
    seguía apareciendo 'MICOPERI DE MEXICO SA DE CV' en vez de 'MICOPERI'.

    No es un dato equivocado, es un dato VIEJO. La solicitud IXT-06102026-0278 se
    procesó antes de que existiera el alias, así que la foto guardó el nombre
    largo, y añadir el alias después no la actualizó. Peor: cambiar un alias mañana
    no arreglaría las solicitudes de hoy, habría que reprocesar 670 PDFs.

    Por eso aquí se resuelve en LECTURA, contra el catálogo vivo: agregar el alias
    cambia lo que se ve, sin tocar una sola fila.

    ── CÓMO DISTINGUE LAS TRES FORMAS DE LA FILA ─────────────────────────

    670 solicitudes, y solo 29 tienen `razonsocial`: las 641 viejas se procesaron
    antes de que esa columna existiera. Por eso hay tres casos, no uno:

      1. `razonsocial` presente  -> es la clave del catálogo. Se resuelve por ahí.
      2. `razonsocial` vacío     -> se intenta con `compania`, que en esas filas
                                    viejas es el nombre largo de origen.
      3. `compania` ya es un alias de otra fila -> se respeta como está, para no
                                    volverlo largo ni inventarle otro.

    El orden importa: `razonsocial` manda sobre `compania` siempre que exista,
    porque es el dato de origen. `compania` es la copia.
    """
    indice = indice_companias()

    razon = (fila.get("razonsocial") or "").strip()
    if razon:
        clave = _normalizar(razon)
        if clave in indice:
            return indice[clave]

    guardada = (fila.get("compania") or "").strip()
    if not guardada:
        return razon

    clave = _normalizar(guardada)
    if clave in indice:
        return indice[clave]
    if clave in _alias_companias:
        # Ya venía abreviada en la base: es el alias de alguna razón social.
        return guardada
    return guardada


def indice_companias() -> dict[str, str]:
    """Diccionario `{razon_social normalizada: alias}`. Cacheado."""
    return _cache_companias.obtener(_cargar_companias)  # type: ignore[return-value]


def obtener_nombre_compania(razon_social: str) -> str:
    """El alias de esta razón social, o la razón social misma si no hay alias.

    Si la razón social no esta en la tabla, se devuelve tal cual: el documento se
    genera igual, solo sin abreviar. Fallar aqui dejaria al usuario sin Excel, que
    es peor que un nombre largo en la celda E8.
    """
    return indice_companias().get(_normalizar(razon_social), (razon_social or "").strip())


def obtener_nombre_compania_existe(razon_social: str) -> bool:
    """¿Esta razón social ya está en el catálogo?

    Lo usa el endpoint de alta para no dejar filas repetidas. La comparación es
    normalizada (minúsculas y sin espacios sobrantes) para que 'MICOPERI DE MEXICO
    SA DE CV' y 'micoperi de mexico sa de cv  ' se consideren la misma.
    """
    return _normalizar(razon_social) in indice_companias()


# ── Activos ────────────────────────────────────────────────────

def _cargar_activos() -> list[str]:
    """Los nombres de la tabla `activos`.

    `leer_activos_supabase()` devuelve YA la lista de strings (`_get("activos",
    select="nombre")` y un `[item["nombre"] for item in res]`), no filas sueltas
    como `leer_companias_supabase`. Por eso aqui no se hace `a.get("nombre")`: se
    toca el elemento tal cual llega.
    """
    return [
        (a or "").strip()
        for a in leer_activos_supabase()
        if (a or "").strip()
    ]


def leer_activos() -> list[str]:
    """Los activos de la tabla `activos`, cacheados. Antes salian del CSV."""
    return list(_cache_activos.obtener(_cargar_activos))  # type: ignore[arg-type]


def contiene_activo(nombre: str) -> bool:
    """¿Este activo existe en el catalogo? Comparacion exacta y normalizada."""
    objetivo = _normalizar(nombre)
    return any(_normalizar(a) == objetivo for a in leer_activos())


# ── Control de la cache ────────────────────────────────────────

def invalidar_cache(companias: bool = True, activos: bool = True) -> None:
    """Fuerza a releer en la proxima llamada.

    Lo llama el backend despues de agregar o borrar desde la UI, para que el
    cambio se vea sin esperar los 5 minutos.
    """
    if companias:
        _cache_companias.invalidar()
    if activos:
        _cache_activos.invalidar()