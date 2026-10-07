"""
core/comandas/ — Modulo de comandas de alimentos al area.

Port de la app de Streamlit (`comandas/app.py`) a logica pura, sin Streamlit y
sin acceso directo a la base de datos. Se compone asi:

    fecha.py       Fechas en espanol, sin depender del locale del servidor.
    parser.py      Lee un PDF de comandas y devuelve datos. No escribe nada.
    stats.py       Agregaciones para el dashboard y el reporte estadistico.
    serie.py       Serie diaria por barco. El barco sale de un mapa de usuarios.
    pdf/           Los cuatro generadores de PDF (el "machote").
    repository.py  Lectura y escritura en Supabase. Unico modulo que toca la BD.

La separacion es deliberada: `parser.py` y `pdf/` son funciones puras sobre
bytes, y por eso se prueban sin base de datos, sin servidor y sin sesion. La
autorizacion vive unicamente en `repository.py`.
"""

from core.comandas.fecha import (
    fecha_largo_es,
    fecha_titulo_es,
    fecha_corta_es,
    hoy_iso,
    resolver_fecha_operacion,
)
from core.comandas.parser import (
    Comanda,
    ResultadoParse,
    ErrorProcesandoPDF,
    parse_pdf,
)
from core.comandas.serie import (
    BARCOS,
    BARCO_POR_USUARIO,
    clasificar_barco,
    serie_diaria,
)
from core.comandas.stats import Estadisticas, calcular_estadisticas

__all__ = [
    "Comanda",
    "ResultadoParse",
    "ErrorProcesandoPDF",
    "parse_pdf",
    "Estadisticas",
    "calcular_estadisticas",
    "BARCOS",
    "BARCO_POR_USUARIO",
    "clasificar_barco",
    "serie_diaria",
    "fecha_largo_es",
    "fecha_titulo_es",
    "fecha_corta_es",
    "hoy_iso",
    "resolver_fecha_operacion",
]
