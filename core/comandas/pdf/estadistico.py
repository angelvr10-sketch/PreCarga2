"""
core/comandas/pdf/estadistico.py — Reporte estadistico en una hoja.

Port de `ComandaApp.generar_reporte_estadistico_bytes` (app.py:1124-1387).
Trae: encabezado, seis tarjetas KPI, un donut de PAX por destino con su leyenda,
barras horizontales de PAX por transporte, y una tabla de companias que se
reparte en varias paginas si no cabe.

Todo el dibujo es reportlab puro (paths, arcos y rectangulos), sin matplotlib ni
plotly: el reporte tiene que salir igual en cualquier maquina y sin fuentes
adicionales en la imagen.
"""

from __future__ import annotations

import io
import math
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from core.comandas.parser import Comanda
from core.comandas.stats import Estadisticas, calcular_estadisticas

MARGEN_X = 40
MARGEN_INFERIOR = 30
ALTO_ENCABEZADO = 80

# ── Paleta ─────────────────────────────────────────────────────
# Vivos y de alto contraste, para imprimir en blanco sin que se apaguen.
VIVIDO_AZUL = colors.Color(0.2, 0.4, 0.8)
VIVIDO_VERDE = colors.Color(0.1, 0.6, 0.3)
VIVIDO_MORADO = colors.Color(0.5, 0.2, 0.7)
VIVIDO_NARANJA = colors.Color(0.9, 0.5, 0.1)
VIVIDO_CIAN = colors.Color(0.0, 0.7, 0.7)
VIVIDO_ROSA = colors.Color(0.8, 0.2, 0.5)
VIVIDO_AMARILLO = colors.Color(0.9, 0.8, 0.1)
VIVIDO_TURQUESA = colors.Color(0.0, 0.5, 0.5)
VIVIDO_ROJO = colors.Color(0.7, 0.1, 0.1)
VIVIDO_INDIGO = colors.Color(0.3, 0.3, 0.6)

PALETA_DONUT = [
    VIVIDO_AZUL, VIVIDO_VERDE, VIVIDO_NARANJA, VIVIDO_MORADO, VIVIDO_CIAN,
    VIVIDO_ROSA, VIVIDO_AMARILLO, VIVIDO_TURQUESA, VIVIDO_ROJO, VIVIDO_INDIGO,
]
PALETA_BARRAS = [
    VIVIDO_AZUL, VIVIDO_VERDE, VIVIDO_NARANJA, VIVIDO_MORADO, VIVIDO_CIAN,
]
RELLENO_TARJETA = [
    colors.Color(0.7, 0.85, 1.0), colors.Color(0.7, 1.0, 0.7),
    colors.Color(1.0, 0.7, 0.7), colors.Color(0.8, 0.7, 1.0),
    colors.Color(0.7, 1.0, 1.0), colors.Color(1.0, 0.7, 0.9),
]
TEXTO_TARJETA = [
    VIVIDO_AZUL, VIVIDO_VERDE, VIVIDO_ROJO, VIVIDO_MORADO,
    VIVIDO_CIAN, VIVIDO_ROSA,
]

TEXTO_OSCURO = colors.Color(0.1, 0.1, 0.2)
TEXTO_SUAVE = colors.Color(0.4, 0.4, 0.5)
TEXTO_PIE = colors.Color(0.55, 0.58, 0.65)

MAX_LEYENDA = 12      # destinos en la leyenda del donut
FILA_ALTO = 18
ENCABEZADO_ALTO = 22
ANCHO_TABLA = 500


def pdf_reporte_estadistico(comandas: list[Comanda], fecha_texto: str,
                            titulo: str) -> bytes:
    """Reporte completo. Paginas: 1 base, +1 por cada tanda extra de companias."""
    s = calcular_estadisticas(comandas)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    _encabezado(c, width, height, titulo, fecha_texto)

    y = height - 95

    y = _tarjetas_kpi(c, width, y, s)
    y_bajo_graficas = _graficas(c, width, y, s)
    _tabla_companias(c, width, height, y_bajo_graficas, s)

    # El pie se dibuja al final, como en el original (app.py:1385). No cambia
    # nada en el papel —la posicion es la misma— pero si el texto se emitiera
    # antes, la extraccion de texto del PDF lo listaria en otro orden y la
    # comparacion contra la app vieja saldría con diferencias fantasma.
    _pie(c, width)

    c.save()
    return buffer.getvalue()


# ── Piezas ─────────────────────────────────────────────────────

def _encabezado(c, width, height, titulo, fecha_texto) -> None:
    fondo = colors.Color(0.9, 0.95, 1.0)
    c.setFillColor(fondo)
    c.rect(0, height - ALTO_ENCABEZADO, width, ALTO_ENCABEZADO, fill=1, stroke=0)

    c.setFillColor(TEXTO_OSCURO)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 35, f"Reporte {titulo}")

    c.setFont("Helvetica", 12)
    c.setFillColor(TEXTO_SUAVE)
    c.drawCentredString(width / 2, height - 55, f"Fecha: {fecha_texto}")


def _tarjetas_kpi(c, width, y, s: Estadisticas) -> float:
    """Las seis tarjetas de resumen, en una sola fila."""
    tarjetas = [
        ("Comandas", str(s.total_comandas)),
        ("Total PAX", str(s.total_alimentos)),
        ("Menú 1", str(s.total_menu1)),
        ("Menú 2", str(s.total_menu2)),
        ("Morteras", str(s.total_mortera)),
        ("Viandas", str(s.total_viandas)),
    ]

    ancho_tarjeta, alto_tarjeta, separacion = 88, 55, 10
    x_inicio = (width - (len(tarjetas) * ancho_tarjeta
                         + (len(tarjetas) - 1) * separacion)) / 2

    for i, (etiqueta, valor) in enumerate(tarjetas):
        x = x_inicio + i * (ancho_tarjeta + separacion)
        y_tarjeta = y - alto_tarjeta

        c.setFillColor(RELLENO_TARJETA[i])
        c.roundRect(x, y_tarjeta, ancho_tarjeta, alto_tarjeta, 10, fill=1, stroke=0)

        c.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
        c.setLineWidth(0.5)
        c.roundRect(x, y_tarjeta, ancho_tarjeta, alto_tarjeta, 10, fill=0, stroke=1)

        c.setFillColor(TEXTO_TARJETA[i])
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(x + ancho_tarjeta / 2, y_tarjeta + alto_tarjeta / 2 + 5, valor)

        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + ancho_tarjeta / 2, y_tarjeta + 12, etiqueta)

    return y - alto_tarjeta - 30


def _graficas(c, width, y, s: Estadisticas) -> float:
    """Donut por destino + leyenda a la izquierda, barras de transporte a la derecha."""
    y_base = _donut(c, MARGEN_X, y, s)
    y_base = _barras(c, width, y, s, y_base)
    return y_base


def _donut(c, x_izq, y, s: Estadisticas) -> float:
    c.setFillColor(TEXTO_OSCURO)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_izq, y, "Distribución de PAX por Destino")

    total = sum(s.por_destino_grafico.values())
    ordenados = sorted(s.por_destino_grafico.items(), key=lambda x: x[1], reverse=True)

    if total <= 0:
        c.setFont("Helvetica", 11)
        c.setFillColor(TEXTO_SUAVE)
        c.drawString(x_izq, y - 25, "Sin datos para graficar.")
        return y - 60

    radio = 75
    cx = x_izq + 80
    cy = y - 100

    angulo_inicio = 90.0
    color_por_destino = {}

    for i, (destino, pax) in enumerate(ordenados):
        color = PALETA_DONUT[i % len(PALETA_DONUT)]
        color_por_destino[destino] = color
        barrido = (pax / total) * 360.0

        c.setFillColor(color)
        ruta = c.beginPath()
        ruta.moveTo(cx, cy)
        # Con muchos destinos el sector puede quedar por debajo de un grado:
        # se fuerza un minimo de 2 puntos para que el path sea valido.
        puntos = max(int(barrido), 2)
        for j in range(puntos + 1):
            ang = math.radians(angulo_inicio - j * barrido / puntos)
            ruta.lineTo(cx + radio * math.cos(ang), cy + radio * math.sin(ang))
        ruta.close()
        c.drawPath(ruta, fill=1, stroke=0)

        # El porcentaje va dentro, pero solo si el sector tiene espacio.
        if barrido > 12:
            medio = math.radians(angulo_inicio - barrido / 2)
            r_texto = radio * 0.65
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 9)
            c.drawCentredString(
                cx + r_texto * math.cos(medio),
                cy + r_texto * math.sin(medio),
                f"{(barrido / 360 * 100):.1f}%",
            )

        angulo_inicio -= barrido

    # Hueco central
    c.setFillColor(colors.white)
    c.circle(cx, cy, radio * 0.4, fill=1, stroke=0)

    c.setFillColor(TEXTO_OSCURO)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(cx, cy + 2, str(total))
    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, cy - 10, "PAX Total")

    # Leyenda
    x_leyenda = x_izq + 160
    y_leyenda = y - 60
    for i, (destino, pax) in enumerate(ordenados[:MAX_LEYENDA]):
        ly = y_leyenda - (i * 15)
        c.setFillColor(color_por_destino.get(destino, TEXTO_SUAVE))
        c.roundRect(x_leyenda, ly, 10, 10, 2, fill=1, stroke=0)

        c.setFillColor(TEXTO_OSCURO)
        c.setFont("Helvetica", 9)
        pct = pax / total * 100
        c.drawString(x_leyenda + 15, ly + 1,
                     f"{destino[:18]} {pax} pax ({pct:.1f}%)")

    return cy - radio - 40


def _barras(c, width, y, s: Estadisticas, y_base: float) -> float:
    x = width * 0.6

    c.setFillColor(TEXTO_OSCURO)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "PAX por Modo de Transporte")

    ordenados = sorted(s.por_transporte.items(), key=lambda x: x[1], reverse=True)
    if not ordenados:
        return y_base

    maximo = max(v for _, v in ordenados) or 1
    ancho_barra, alto_barra, separacion = 100, 18, 12

    by = y - 60
    for i, (transporte, pax) in enumerate(ordenados):
        color = PALETA_BARRAS[i % len(PALETA_BARRAS)]
        ancho_relleno = max(5, (pax / maximo) * ancho_barra)

        c.setFillColor(colors.Color(0.9, 0.9, 0.95))
        c.roundRect(x + 80, by, ancho_barra, alto_barra, 4, fill=1, stroke=0)

        c.setFillColor(color)
        c.roundRect(x + 80, by, ancho_relleno, alto_barra, 4, fill=1, stroke=0)

        c.setFillColor(TEXTO_OSCURO)
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(x + 75, by + 12, transporte)
        c.drawString(x + 85 + ancho_relleno, by + 12, f"{pax} pax")

        by -= alto_barra + separacion

    # La tabla de companias empieza debajo de lo mas bajo entre las dos graficas.
    return by - 30 if by < (y - 100) else y - 220


def _tabla_companias(c, width, height, y, s: Estadisticas) -> None:
    """Tabla por compania, repartida en paginas si no cabe en la primera."""
    c.setFillColor(TEXTO_OSCURO)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y - 30, "Detalle por Compañía")

    if not s.por_compania:
        c.setFont("Helvetica", 11)
        c.setFillColor(TEXTO_SUAVE)
        c.drawCentredString(width / 2, y - 55, "Sin companias registradas.")
        return

    datos = [["Compañía", "PAX", "% del Total"]]
    for compania, pax in sorted(s.por_compania.items(), key=lambda x: x[1], reverse=True):
        porcentaje = (pax / s.total_alimentos * 100) if s.total_alimentos else 0
        datos.append([compania, str(pax), f"{porcentaje:.1f}%"])

    encabezado = datos[0]
    pendientes = datos[1:]
    x_tabla = (width - ANCHO_TABLA) / 2

    primera = True
    while pendientes:
        espacio = (y - MARGEN_INFERIOR - 30) if primera \
            else (height - ALTO_ENCABEZADO - MARGEN_INFERIOR)
        max_filas = max(1, int((espacio - ENCABEZADO_ALTO) / FILA_ALTO))
        trozo = pendientes[:max_filas]
        pendientes = pendientes[max_filas:]

        tabla = Table([encabezado] + trozo, colWidths=[320, 80, 80])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VIVIDO_AZUL),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWHEIGHT', (0, 0), (-1, -1), FILA_ALTO),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.9)),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.Color(0.97, 0.98, 1.0)]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        tabla.wrapOn(c, ANCHO_TABLA, espacio)

        if primera:
            y -= 60
        else:
            y = height - 130

        # `_height` es un atributo interno de reportlab, no parte de su API
        # publica. Se lee con getattr y, si en una version futura desaparece,
        # se calcula desde las alturas de fila declaradas.
        alto_real = getattr(tabla, '_height', None)
        if alto_real is None:
            alto_real = ENCABEZADO_ALTO + FILA_ALTO * len(trozo)

        tabla.drawOn(c, x_tabla, y - alto_real)
        y -= alto_real + 20

        if pendientes:
            # Pagina de continuacion: solo pie, sin encabezado repetido.
            # Es lo que hacia el original (app.py:1379-1383).
            _pie(c, width)
            c.showPage()
            primera = False
            y = height - 120


def _pie(c, width) -> None:
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(TEXTO_PIE)
    c.drawRightString(width - MARGEN_X, 15, "ComandasPro v1.0")
    c.drawCentredString(width / 2, 15, "Angel Valenzuela Romero © 2026")
    c.drawString(MARGEN_X, 15,
                 f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
