"""
core/comandas/tabla.py — Lectura del concentrado de comandas por COLUMNAS.

Por que existe: `parser.py` aplana el texto del PDF a una sola linea y luego
busca las comandas con regex. Aplanar mete saltos de linea en lugares que no
siguen las filas, y en un reporte de 52 comandas eso mete ruido suficiente para
corromper numeros. En el concentrado del 14-10-2026:

  1. `pypdf` partio un `13` en `1 3`, y el regex leyo 3 personas de mas
    _dimension. La suma de PAX salio 517 en vez de 527.
  2. La fila de SUBTOTAL de cada bloque (`36 36 00`) quedo pegada a la ultima
     fila de datos del bloque, y dos de sus numeros cayeron en la columna
     MENU 2: 121 de comida que en el papel no existe.

Las dos cosas vienen de la misma causa: al perder la geometria, el texto ya no
sabe que numero era de que columna. Este modulo no aplana nada. Lee cada palabra
con su coordenada X y decide a que columna pertenece, que es justo la
informacion que `extract_text()` destruye.

Que NO cambia: `parser.py` sigue siendo quien arma los `Comanda`, quien aplica
la regla `menu_1 = pax`, quien limpia las observaciones y quien resuelve la
fecha. Aqui solo se decide que palabra es el folio y cuales son sus numeros.

De donde salen los limites de columna: de la geometria de la plataforma, que es
fija. Los cuatro concentrados reales (julio, agosto y septiembre de 2026, y el
de octubre) son 595x792 y traen el encabezado en las mismas X:

    NO. COM.  HORARIO  DEPARTAMENTO/COMPAÑIA  DESTINO  No.  PAX  TRANSPORTE  MENU 1  MENU 2  CUSTODIO  OBSERVACIONES
    32   45    73       115                    231      288   300  330         385     419     451       500

Los limites de este archivo son los puntos medios entre esos anclajes. La banda
de MENU 2 corta en 470 porque la columna CUSTODIO no trae dato en ningun
reporte de la plataforma: ahi solo caen la palabra del encabezado y el dia de la
fecha del pie, y ninguna de las dos debe leerse como un menu.

La banda de DESTINO empieza en 225, no antes, porque hay un destino que se
llama `ABKATUN-N1` y cuya palabra cae justo ahi. Si el limite se correria a la
izquierda, ese destino se leeria partido en dos.

── LO QUE ESTE MODULO NO LEE, Y POR QUE ───────────────────────────────────

La columna de OBSERVACIONES queda fuera a proposito. Si se intentara, habria
que separar las lineas de un bloque de las del bloque siguiente, y los cuatro
concentrados no dan margen:

  - En `ComandaAlimentos(2).pdf` las filas van cada 13.8 puntos y las
    observaciones son UNA linea por fila. Entre bloque y bloque hay 13.8.
  - En `ComandaAlimentos.pdf` las observaciones de JUL026 ocupan SEIS lineas
    (de la 368 a la 412) centradas en su fila, que esta en la 390. Entre linea
    y linea dentro del bloque hay de 8 a 12 puntos.

Los dos casos quedan separados por 1.8 puntos. Un umbral sirve para uno y
rompe el otro, y equivocarse no es un detalle: `MORTERA` en las observaciones
es lo que decide el `tipo` de la comanda. Perder media linea de texto cambia
una MORTERA por VIANDA en el reporte estadistico y en el machote.

Por eso las observaciones las sigue Sacando `parser.observaciones_por_folio`,
que trabaja sobre el texto plano y no depende de la geometria. Aqui solo se
leen los campos que estan EN la linea de la fila, que es donde estaba el bug.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

import pdfplumber

# ── Limites de columna ──────────────────────────────────────────
# (x_inicial, x_final) en puntos, sobre la pagina de 595x792 de la plataforma.
# Final exclusivo. Se derivan del encabezado de la tabla; ver la cabecera.
#
# NO esta la columna de observaciones, y es deliberado. Ver "LO QUE ESTE
# MODULO NO LEE" mas abajo.

COL_FOLIO = (25, 70)
COL_HORARIO = (70, 110)
COL_COMPANIA = (110, 225)
COL_DESTINO = (225, 280)
COL_PAX = (280, 322)
COL_TRANSPORTE = (322, 375)
COL_MENU1 = (375, 415)
COL_MENU2 = (415, 470)

# Dos palabras son la misma linea visual si sus baselines caen a menos de esto.
# Tres puntos separa las lineas de una fila sin partir las palabras de una
# misma linea, que llegan a separarse 0.4 puntos entre si por tener distinto
# tamano de fuente.
TOL_LINEA = 3.0

# ── Vocabulario ─────────────────────────────────────────────────

TRANSPORTES = frozenset({"AEREO", "GANGWAY", "MARÍTIMO", "VIUDA", "CANASTILLA"})

RE_FOLIO = re.compile(r"[A-Z]{3}\d{2,6}")
RE_HORARIO = re.compile(r"\d{1,2}:\d{2}")
RE_PAX = re.compile(r"\d{1,3}")


class ErrorTabla(ValueError):
    """El PDF no se pudo leer como tabla: no es un concentrado, o el layout
    cambio y esta version de las columnas no lo reconoce."""


@dataclass(frozen=True)
class Fila:
    """Una fila del concentrado, tal como sale de la pagina.

    No es un `Comanda`: falta la regla `menu_1 = pax`, las observaciones y el
    `tipo`. Eso es de `parser.py`, que es quien arma los `Comanda`. Aqui no hay
    criterio de negocio, solo geometria.
    """
    folio: str
    horario: str
    compania: str
    destino: str
    pax: int
    transporte: str
    menu_1: int
    menu_2: int


# ── Utilidades de columna ───────────────────────────────────────

def _en_linea(palabras: list[dict], columna: tuple[float, float]) -> str:
    """El texto de las palabras de `palabras` que caen dentro de `columna`."""
    x0, x1 = columna
    return " ".join(
        p["text"] for p in palabras if x0 <= p["x0"] < x1
    ).strip()


def _unir(palabras: list[dict]) -> str:
    """Varias palabras en una sola palabra, sin espacios de mas.

    El destino `ABKATUN D` son dos palabras en la pagina, pero es un destino
    solo. Sin esta normalizacion, buscarlo en el texto plano no lo encontraria.
    """
    return " ".join(p["text"] for p in palabras).strip()


def _lineas(palabras: list[dict]) -> list[list[dict]]:
    """Agrupa palabras por linea visual, usando su baseline (`top`).

    `extract_words()` no devuelve lineas, sino palabras sueltas. Se agrupan por
    `top` con una tolerancia de 3 puntos, que es lo que separa dos filas de la
    tabla sin partir las palabras de una misma fila.
    """
    ordenadas = sorted(palabras, key=lambda p: (p["top"], p["x0"]))
    grupos: list[list[dict]] = []
    actual: list[dict] = []
    for palabra in ordenadas:
        if actual and palabra["top"] - actual[-1]["top"] <= TOL_LINEA:
            actual.append(palabra)
        else:
            if actual:
                grupos.append(actual)
            actual = [palabra]
    if actual:
        grupos.append(actual)
    return grupos


# ── Lectura ─────────────────────────────────────────────────────

def _es_fila_de_datos(palabras: list[dict]) -> bool:
    """Una fila de datos trae folio en su columna y un transporte conocido.

    Las dos condiciones juntas descartan los encabezados de tabla (que traen la
    palabra 'MENU' pero ningun folio), las filas de subtotal (que traen tres
    numeros pero ningun folio) y el titulo del reporte.
    """
    folio = _en_linea(palabras, COL_FOLIO)
    if not RE_FOLIO.fullmatch(folio):
        return False
    return _en_linea(palabras, COL_TRANSPORTE).strip() in TRANSPORTES


def _filas_de_pagina(pagina) -> list[Fila]:
    lineas = _lineas(pagina.extract_words())

    filas: list[Fila] = []
    incompletas: list[str] = []
    for linea in lineas:
        if not _es_fila_de_datos(linea):
            continue
        folio = _en_linea(linea, COL_FOLIO)
        pax = _en_linea(linea, COL_PAX)
        menu_1 = _en_linea(linea, COL_MENU1)
        menu_2 = _en_linea(linea, COL_MENU2)
        if not (RE_PAX.fullmatch(pax) and RE_PAX.fullmatch(menu_2)):
            # Una fila con folio y transporte pero sin numeros legibles es un
            # layout que esta version de columnas no conoce. No se inventa el
            # valor: se deja la fila fuera y se avisa.
            incompletas.append(folio)
            continue

        filas.append(Fila(
            folio=folio,
            horario=_en_linea(linea, COL_HORARIO).strip(),
            compania=_unir([p for p in linea
                            if COL_COMPANIA[0] <= p["x0"] < COL_COMPANIA[1]]),
            destino=_unir([p for p in linea
                           if COL_DESTINO[0] <= p["x0"] < COL_DESTINO[1]]),
            pax=int(pax),
            transporte=_en_linea(linea, COL_TRANSPORTE).strip(),
            # MENU 1 se lee igual, aunque `parser.py` no lo use: deja el dato
            # disponible para comparar PAX contra MENU 1 sin volver al PDF.
            menu_1=int(menu_1) if RE_PAX.fullmatch(menu_1) else int(pax),
            menu_2=int(menu_2),
        ))

    if not filas and incompletas:
        raise ErrorTabla(
            f"{len(incompletas)} fila(s) con folio y transporte pero sin numeros "
            f"legibles en sus columnas (p.ej. {', '.join(incompletas[:5])}). "
            f"El layout del concentrado cambio."
        )
    return filas


def leer_tabla(file_bytes: bytes) -> list[Fila]:
    """Las filas del concentrado, leidas por columnas.

    Devuelve una lista vacia si el PDF es valido pero no tiene la tabla de
    comandas (por ejemplo, un machote de una sola comanda). Lanza `ErrorTabla`
    si no se puede leer el archivo, para que quien llame decida si degrada a
    la lectura por texto plano.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            filas: list[Fila] = []
            for pagina in pdf.pages:
                filas.extend(_filas_de_pagina(pagina))
    except ErrorTabla:
        raise
    except Exception as exc:
        raise ErrorTabla(f"No se pudo leer el PDF como tabla: {exc}") from exc
    return filas