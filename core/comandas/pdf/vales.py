"""
core/comandas/pdf/vales.py — Vales de alimentos, 10 por hoja.

Port de `ComandaApp.generar_vales_pdf_bytes` (app.py:936-1122). Cada vale lleva
firmas de administracion para recibir en destino, asi que la posicion de cada
linea esta calculada sobre la celda: si cambia una constante, cambia el papel.

Layout: 2 columnas x 5 filas sobre letter (612 x 792 pt).
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from core.comandas.fecha import fecha_corta_desde_texto_pdf, fecha_corta_es, hoy
from core.comandas.parser import Comanda

# ── Layout ─────────────────────────────────────────────────────
COLUMNAS = 2
FILAS = 5
VALES_POR_PAGINA = COLUMNAS * FILAS      # 10

MARGEN_X = 28
MARGEN_Y = 18
SEPARACION = 4     # hueco visible entre vales vecinos
PADDING = 8

# ── Tamano de letra ────────────────────────────────────────────
F_ETIQUETA = 8.5
F_VALOR = 10
F_TITULO = 10.5
F_MARCA = 8
F_FIRMA = 8

AZUL_CORP = colors.Color(0.08, 0.08, 0.35)
AZUL_VALOR = colors.Color(0.05, 0.10, 0.50)
GRIS_LINEA = colors.Color(0.55, 0.55, 0.55)
GRIS_SUAVE = colors.Color(0.35, 0.35, 0.35)

MAX_COMPANIA = 24
MAX_DESTINO = 16


def pdf_vales(comandas: list[Comanda], fecha_texto: str = "") -> bytes:
    """Hojas de vales, 10 por pagina, ordenadas por folio."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    ordenadas = sorted(comandas, key=lambda x: x.comanda)

    ancho_area = width - 2 * MARGEN_X
    alto_area = height - 2 * MARGEN_Y
    ancho_celda = ancho_area / COLUMNAS
    alto_celda = alto_area / FILAS

    ancho_vale = ancho_celda - SEPARACION
    alto_vale = alto_celda - SEPARACION

    fecha_corta = fecha_corta_desde_texto_pdf(fecha_texto) or fecha_corta_es(hoy())

    for indice, comanda in enumerate(ordenadas):
        posicion = indice % VALES_POR_PAGINA
        if posicion == 0 and indice > 0:
            c.showPage()

        fila = posicion // COLUMNAS
        columna = posicion % COLUMNAS

        # Esquina inferior izquierda de la celda
        x0 = MARGEN_X + columna * ancho_celda + (SEPARACION / 2)
        y0 = height - MARGEN_Y - (fila + 1) * alto_celda + (SEPARACION / 2)

        _dibujar_vale(c, comanda, x0, y0, ancho_vale, alto_vale, fecha_corta)

    c.save()
    return buffer.getvalue()


def _dibujar_vale(c, comanda: Comanda, x0, y0, vale_w, vale_h, fecha_corta) -> None:
    # Borde del vale
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.9)
    c.rect(x0, y0, vale_w, vale_h, fill=0, stroke=1)

    # ── Encabezado ─────────────────────────────────────────────
    alto_hdr = 26
    y_hdr = y0 + vale_h - alto_hdr

    c.setFillColor(colors.white)
    c.rect(x0, y_hdr, vale_w, alto_hdr, fill=1, stroke=0)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", F_TITULO)
    c.drawCentredString(x0 + vale_w / 2, y_hdr + 9, "ALIMENTOS AL AREA")

    c.setFont("Helvetica-Bold", F_MARCA)
    c.setFillColor(AZUL_CORP)
    c.drawString(x0 + PADDING, y_hdr + 9, "KOLTOV")
    c.drawRightString(x0 + vale_w - PADDING, y_hdr + 9, "SHAT")

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.7)
    c.line(x0, y_hdr, x0 + vale_w, y_hdr)

    # ── Zona de firma (parte baja fija) ────────────────────────
    alto_firma = 28
    y_linea_firma = y0 + alto_firma - 10

    ancho_firma = vale_w * 0.60
    x_firma = x0 + (vale_w - ancho_firma) / 2
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.6)
    c.line(x_firma, y_linea_firma, x_firma + ancho_firma, y_linea_firma)

    c.setFont("Helvetica-Bold", F_FIRMA)
    c.setFillColor(colors.black)
    c.drawCentredString(x0 + vale_w / 2, y_linea_firma - 9, "ADMINISTRACION")

    # ── Zona de campos: tres filas entre el encabezado y la firma ─
    tope_cuerpo = y_hdr - 6
    base_cuerpo = y0 + alto_firma + 4
    alto_cuerpo = tope_cuerpo - base_cuerpo
    alto_fila = alto_cuerpo / 3

    fx = x0 + PADDING
    fw = vale_w - 2 * PADDING

    def linea(ly, lx1, lx2):
        c.setStrokeColor(GRIS_LINEA)
        c.setLineWidth(0.5)
        c.line(lx1, ly - 2, lx2, ly - 2)

    def campo(ly, etiqueta, valor, x_etiqueta, x_linea, ancho_valor):
        c.setFont("Helvetica-Bold", F_ETIQUETA)
        c.setFillColor(colors.black)
        c.drawString(x_etiqueta, ly, etiqueta)

        c.setFont("Helvetica-Bold", F_VALOR)
        c.setFillColor(AZUL_VALOR)
        c.drawString(x_etiqueta + ancho_valor, ly, valor)
        linea(ly, x_etiqueta + ancho_valor - 2, x_linea)

    # Fila 1: FECHA | No. DE COMANDA
    y1 = tope_cuerpo - alto_fila * 0.55
    corte1 = fx + fw * 0.46
    campo(y1, "FECHA:", fecha_corta, fx, corte1 - 4, 40)
    campo(y1, "No. COMANDA:", "  " + comanda.comanda, corte1 + 4, fx + fw, 82)

    # Fila 2: COMPAÑÍA | PAX
    y2 = y1 - alto_fila
    corte2 = fx + fw * 0.72
    compania = _recortar(comanda.compania, MAX_COMPANIA)
    campo(y2, "COMPAÑÍA:", "    " + compania, fx, corte2 - 4, 52)
    campo(y2, "PAX:", f"   {comanda.pax}", corte2 + 4, fx + fw, 28)

    # Fila 3: DESTINO | MENÚ
    y3 = y2 - alto_fila
    corte3 = fx + fw * 0.56
    destino = _recortar(comanda.destino, MAX_DESTINO)
    campo(y3, "DESTINO:", "    " + destino, fx, corte3 - 4, 46)
    campo(y3, "MENÚ:", "   " + _menu(comanda), corte3 + 4, fx + fw, 34)


def _menu(comanda: Comanda) -> str:
    """'M1  M2' segun que menús lleva la comanda, o un guion si no lleva ninguno."""
    partes = []
    if comanda.menu_1 > 0:
        partes.append("    M1")
    if comanda.menu_2 > 0:
        partes.append("    M2")
    return "   ".join(partes) if partes else "—"


def _recortar(texto: str, limite: int) -> str:
    """Recorta con puntos suspensivos si el texto no cabe en el campo."""
    texto = texto or ''
    return texto[:limite] + ("…" if len(texto) > limite else "")
