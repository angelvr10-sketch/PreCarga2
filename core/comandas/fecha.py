"""
core/comandas/fecha.py — Fechas en español, sin depender del locale del servidor.

Por que existe este modulo: la app de Streamlit mezclaba dos criterios. En unos
sitios usaba arrays de meses en espanol (correcto) y en otros `strftime("%B")`,
que devuelve el mes en el idioma del sistema: en un contenedor sin locale
`es_MX` sale "October", no "OCTUBRE", y el PDF del machote se va al papel con el
mes en ingles. `strftime` con `%B` NO es portable.

Regla que manda aqui: ningun modulo de comandas llama a `strftime("%B")` ni a
`strftime("%A")`. Todo pasa por estas funciones.
"""

from __future__ import annotations

import re
from datetime import date, datetime

# ── Vocabulario ────────────────────────────────────────────────
# index 0 = lunes, para alinearlo con `date.weekday()`. Python define lunes=0.
#
# OJO con los acentos: MIÉRCOLES y SÁBADO van CON acento, y es lo que imprime la
# app original (app.py:358). Helvetica de reportlab los dibuja sin problema y
# quitarlos cambia el papel que se firma. Una version anterior de este archivo
# normalizaba a 'MIERCOLES'; el golden set
# (tests/fixtures/Todas_las_Comandas_REFORMA_PEMEX.pdf, pagina 1) demuestra que
# el original escribe 'MIÉRCOLES'.
DIAS_ES: tuple[str, ...] = (
    "LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO",
)

# En minusculas y con acentos, para la interfaz.
DIAS_ES_TITULO: tuple[str, ...] = (
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
)

# Ningun mes en espanol lleva acento, asi que se comparan tal cual.
MESES_ES: tuple[str, ...] = (
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
)

# Indice 1..12 (0 sin usar) para traducir "MAYO" -> "05".
MES_A_NUMERO: dict[str, int] = {m: i + 1 for i, m in enumerate(MESES_ES)}

# Formatos de fecha que aparecen en la cabecera del PDF de comandas.
_FORMATO_FECHA_PDF = re.compile(r"(\w+,\s*\d{1,2}\s+de\s+\w+\s+de\s+\d{4})", re.IGNORECASE)


class FechaNoReconocida(ValueError):
    """El texto del PDF no traia una fecha legible."""


# ── Construccion ───────────────────────────────────────────────

def fecha_largo_es(fecha: date) -> str:
    """'MARTES, 13 DE MAYO DE 2026' — el formato que pide el machote.

    Acepta `date` o `datetime`. Conserva los acentos del dia de la semana
    ('MIÉRCOLES'), igual que la app original.
    """
    return (
        f"{DIAS_ES[fecha.weekday()]}, {fecha.day} DE "
        f"{MESES_ES[fecha.month - 1]} DE {fecha.year}"
    )


def fecha_titulo_es(fecha: date) -> str:
    """'martes, 13 de mayo de 2026' — para la interfaz, con acentos y minúsculas."""
    return (
        f"{DIAS_ES_TITULO[fecha.weekday()]}, {fecha.day} de "
        f"{MESES_ES[fecha.month - 1].lower()} de {fecha.year}"
    )


def fecha_corta_es(fecha: date) -> str:
    """'13/05/2026' — la que va en los vales."""
    return f"{fecha.day:02d}/{fecha.month:02d}/{fecha.year}"


def hoy() -> date:
    return datetime.now().date()


def hoy_iso() -> str:
    return hoy().isoformat()


# ── Lectura de la fecha que viene dentro del PDF ───────────────

def texto_fecha_del_pdf(texto: str) -> str | None:
    """Extrae la fecha del pie del reporte, o None si no esta.

    Acepta 'viernes, 3 de julio de 2026' en cualquier combinacion de
    mayusculas y devuelve el texto en mayusculas y TAL CUAL, acentos incluidos.

    No se quitan los acentos: el dia de la semana se dibuja despues en el
    machote y ahi si lleva ('MIÉRCOLES'). Los meses no llevan acento, asi que
    no hacen falta para nada mas.
    """
    m = _FORMATO_FECHA_PDF.search(texto)
    if not m:
        return None
    return m.group(1).strip().upper()


def iso_desde_texto_pdf(texto_fecha: str) -> str | None:
    """'LUNES, 13 DE MAYO DE 2026' -> '2026-05-13'. None si no cuadra.

    El texto puede venir con o sin el dia de la semana delante. Se descarta
    y se leen dia/mes/anio posicionalmente, que es como lo hacia la app original.
    """
    if not texto_fecha:
        return None
    try:
        # Quitar el dia de la semana: 'LUNES, 13 DE MAYO DE 2026' -> '13 DE MAYO DE 2026'
        partes = texto_fecha.split(",")
        parte_fecha = partes[1].strip() if len(partes) > 1 else partes[0].strip()

        # '13 DE MAYO DE 2026' -> '13 MAYO 2026'
        limpio = parte_fecha.replace(" DE ", " ")

        tokens = limpio.split()
        if len(tokens) != 3:
            return None

        dia, mes, anio = tokens
        mes_num = MES_A_NUMERO.get(mes.upper())
        if mes_num is None:
            return None

        return f"{anio}-{mes_num:02d}-{int(dia):02d}"
    except (ValueError, IndexError):
        return None


def fecha_corta_desde_texto_pdf(texto_fecha: str) -> str | None:
    """'LUNES, 13 DE MAYO DE 2026' -> '13/05/2026'. Para los vales."""
    iso = iso_desde_texto_pdf(texto_fecha)
    if not iso:
        return None
    try:
        return fecha_corta_es(datetime.strptime(iso, "%Y-%m-%d").date())
    except ValueError:
        return None


# ── Fecha de operacion: la del PDF, o la de hoy si el PDF no la trae ──

def resolver_fecha_operacion(texto_pdf: str) -> tuple[str, str]:
    """ Decide que fecha se usa para las comandas.

    Devuelve (fecha_iso, fecha_texto_machote).

    Prioridad: la fecha que viene en el PDF > la fecha de hoy. Si el PDF no
    trae fecha se usa hoy, que es lo que hacia la app original. La fecha_texto
    siempre queda lista para dibujar en el machote, nunca vacia.
    """
    texto = texto_fecha_del_pdf(texto_pdf)
    if texto:
        iso = iso_desde_texto_pdf(texto)
        if iso:
            return iso, fecha_largo_es(datetime.strptime(iso, "%Y-%m-%d").date())
        # Habia texto de fecha pero no se pudo convertir a ISO (mes raro,
        # formato inesperado): se conserva el texto tal cual para el PDF y se
        # guarda bajo hoy, que es el comportamiento previo.
        return hoy_iso(), fecha_largo_es(hoy())

    return hoy_iso(), fecha_largo_es(hoy())
