"""
core/comandas/pdf/comanda.py — El machote de una comanda.

Port de los metodos reportlab de la app de Streamlit:
  _dibujar_header_machote            (app.py:603-668)
  _dibujar_tabla_datos               (app.py:671-695)
  _dibujar_tablas_utensilios         (app.py:697-735)
  _dibujar_bloque_firmas_estandar    (app.py:737-758)
  _dibujar_comanda_en_canvas         (app.py:762-803)
  _dibujar_comanda_mortera_en_canvas (app.py:821-918)

Las coordenadas estan en puntos (1 pt = 1/72 pulgada) sobre papel letter
(612 x 792 pt). CADA NUMERO DE ESTE ARCHIVO COPIA EL ORIGINAL. Un cambio de
posicion se ve en el papel firmado por personas, asi que no se "mejora" nada sin
una maqueta firmada de referencia con la que comparar.

Lo unico que cambio respecto al original: los metodos eran de una clase con
`self` para leer `self.fecha_pdf` y `self.titulo_proyecto`. Aqui son funciones
de modulo que reciben ambos como argumentos, lo que permite probarlas sin
construir nada antes.
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from core.comandas.parser import Comanda

# ── Constantes del machote ─────────────────────────────────────
# Todas vienen del original. No "simplificar".

MARGEN_LATERAL = 28
CONTRATO = "CONTRATO No. 428224804"
MARCA_IZQUIERDA = "KOL TOV"
MARCA_DERECHA = "SHAT"
PIE_PAGINA = "Angel Valenzuela Romero © 2026"

# Posiciones de las dos columnas de firmas (fracciones del ancho de la pagina).
COL_SIG_1 = 0.27
COL_SIG_2 = 0.73
ANCHO_LINEA_SIG = 185

# Separacion vertical entre los dos pares de firmas.
SEP_PARES = 120

# Bloque MORTERA: seis lineas extra encima de "ENTREGA ALIMENTOS".
ETIQUETAS_MORTERA = (
    "ELABORÓ",
    "SUPERVISÓ",
    "AUTORIZÓ",
    "RECIBIÓ MORTERA",
    "ENTREGÓ MORTERA",
    "OPERADOR RESPONSABLE",
)
SEP_FIRMAS_MORTERA = 30
ANCHO_FIRMA_MORTERA = 200

# ── BUG HEREDADO, A PROPÓSITO ──────────────────────────────────
# La app de Streamlit recorría las seis etiquetas, dibujaba la línea de firma de
# cada una... y nunca escribía el texto. `app.py:904` asignaba `etiq` y saltaba
# directo al `c.line(...)`; no habia ningun `drawCentredString`. El resultado en
# el papel son seis rayas en blanco: la gente firma sin saber que firma.
#
# Aqui las lineas se siguen dibujando exactamente igual, y la etiqueta se
# escribe solo si se activa este interruptor. Por defecto False = el papel de
# siempre. Ponerlo en True cambia el machote, asi que es una decision de
# operacion, no un bugfix silencioso.
DIBUJAR_ETIQUETAS_MORTERA = False

GRIS_CABECERA = colors.Color(0.82, 0.82, 0.82)


# ── Piezas del machote ─────────────────────────────────────────

def _dibujar_header(c, width, height, fecha_texto, titulo, folio) -> float:
    """Encabezado con marcas, titulo, fecha subrayada y folio grande.

    Devuelve la coordenada Y libre para seguir dibujando debajo.
    """
    # Marcas a los lados. El original dibujaba las imagenes de los logos y
    # cayo en texto plano; se conserva el texto, que es lo que esta impreso.
    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(0.8, 0.1, 0.1)
    c.drawString(MARGEN_LATERAL, height - 55, MARCA_IZQUIERDA)
    c.drawRightString(width - MARGEN_LATERAL, height - 55, MARCA_DERECHA)

    # Titulo centrado
    cx = width / 2
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(cx, height - 48, titulo)
    c.setFont("Helvetica", 9)
    c.drawCentredString(cx, height - 60, CONTRATO)

    # Linea separadora
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.setLineWidth(0.5)
    c.line(MARGEN_LATERAL, height - 70, width - MARGEN_LATERAL, height - 70)

    # Fecha, centrada como bloque (etiqueta + valor) y subrayada bajo el valor
    etiqueta = "CONTROL DE ENTREGA DE ALIMENTOS AL AREA DEL DIA: "
    valor = fecha_texto.upper()

    ancho_etiqueta = c.stringWidth(etiqueta, "Helvetica", 9)
    ancho_valor = c.stringWidth(valor, "Helvetica-Bold", 9)
    x_inicio = (width - (ancho_etiqueta + ancho_valor)) / 2
    y_fecha = height - 82

    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(x_inicio, y_fecha, etiqueta)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_inicio + ancho_etiqueta, y_fecha, valor)

    c.setLineWidth(0.8)
    c.line(
        x_inicio + ancho_etiqueta, y_fecha - 2,
        x_inicio + ancho_etiqueta + ancho_valor, y_fecha - 2,
    )

    # Folio grande, centrado, sobre fondo blanco
    y_folio = height - 115
    tam_folio = 22
    ancho_folio = c.stringWidth(folio, "Helvetica-Bold", tam_folio)
    pad_x, pad_y = 14, 5

    rect_x = (width - ancho_folio) / 2 - pad_x
    rect_y = y_folio - pad_y
    rect_w = ancho_folio + pad_x * 2
    rect_h = tam_folio + pad_y * 2 - 2

    c.setFillColorRGB(1.0, 1.0, 1.0)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    c.rect(rect_x, rect_y, rect_w, rect_h, fill=1, stroke=0)

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", tam_folio)
    c.drawCentredString(width / 2, y_folio, folio)

    return height - 135


def _dibujar_observaciones(c, width, y, observaciones: str) -> float:
    """Bloque opcional de observaciones. Centrado, partido en lineas de 95."""
    texto = (observaciones or '').strip()
    if not texto:
        return y - 2

    y -= 4
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawCentredString(width / 2, y, "OBSERVACIONES:")

    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.1, 0.1, 0.5)

    lineas: list[str] = []
    for parte in texto.split(' | '):
        while len(parte) > 95:
            lineas.append(parte[:95])
            parte = parte[95:]
        if parte:
            lineas.append(parte)

    for linea in lineas:
        y -= 11
        c.drawCentredString(width / 2, y, linea)

    return y - 12


def _dibujar_tabla_datos(c, width, comanda, y_top) -> float:
    """Tabla DESTINO / DEPARTAMENTO-COMPAÑIA / NO. PERSONAS / MENU 1 / MENU 2."""
    datos = [
        ['DESTINO', 'DEPARTAMENTO/COMPAÑÍA', 'NO. PERSONAS', 'MENU 1', 'MENU 2'],
        [
            comanda.destino,
            comanda.compania,
            str(comanda.pax),
            str(comanda.menu_1),
            str(comanda.menu_2),
        ],
    ]
    anchos = [100, 195, 90, 60, 60]

    tabla = Table(datos, colWidths=anchos, rowHeights=[16, 18])
    tabla.setStyle(TableStyle([
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), GRIS_CABECERA),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',       (0, 0), (-1, -1), 0.6, colors.black),
        ('FONTNAME',   (0, 1), (-1, 1), 'Helvetica-Bold'),
    ]))

    margen = (width - sum(anchos)) / 2
    tabla.wrapOn(c, width, 200)
    tabla.drawOn(c, margen, y_top - 34)

    return y_top - 40


def _dibujar_tablas_utensilios(c, width, y_top) -> float:
    """Las dos tablas SALIDA / DEVOLUCION, lado a lado."""
    filas = [
        ['PORTA VIANDA', ''],
        ['MORTERA', ''],
        ['THERMO MCA. IGLOO 3 LT', ''],
        ['THERMO MCA. IGLOO 19 LT', ''],
        ['PARA SERVIR ALIMENTOS\nDE ACERO INOX.', ''],
        ['PINZAS PARA ENSALADAS', ''],
        ['INSERTOS DE AC. INOXIDABLE', ''],
        ['TOTAL ARTICULOS', ''],
    ]

    anchos = [155, 45]
    alturas = [16] + [22] * len(filas)

    for x_offset, titulo in [(55, "SALIDA"), (333, "DEVOLUCIÓN")]:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(x_offset + sum(anchos) / 2, y_top + 2, titulo)

        tabla = Table([['DESCRIPCION', 'CANTIDAD']] + filas,
                      colWidths=anchos, rowHeights=alturas)
        tabla.setStyle(TableStyle([
            ('FONTNAME',   (0, 0), (-1,  0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (-1,  0), GRIS_CABECERA),
            ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), GRIS_CABECERA),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',       (0, 0), (-1, -1), 0.5, colors.black),
            ('WORDWRAP',   (0, 0), (-1, -1), True),
        ]))
        tabla.wrapOn(c, 300, 500)
        tabla.drawOn(c, x_offset, y_top - sum(alturas))

    return y_top - sum(alturas) - 16


def _par_de_firmas(c, width, y, etiqueta_izq, etiqueta_der) -> None:
    """Un par de lineas de firma con su leyenda."""
    col1 = width * COL_SIG_1
    col2 = width * COL_SIG_2

    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.8)
    c.line(col1 - ANCHO_LINEA_SIG / 2, y, col1 + ANCHO_LINEA_SIG / 2, y)
    c.line(col2 - ANCHO_LINEA_SIG / 2, y, col2 + ANCHO_LINEA_SIG / 2, y)

    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(col1, y - 13, etiqueta_izq)
    c.drawCentredString(col2, y - 13, etiqueta_der)

    c.setFont("Helvetica", 7)
    c.drawCentredString(col1, y - 23, "NOMBRE Y FIRMA")
    c.drawCentredString(col2, y - 23, "NOMBRE Y FIRMA")


def _firma_estandar(c, width, y_base) -> None:
    """RECIBE ALIMENTOS / ENTREGA UTENSILIOS arriba, ENTREGA / RECIBE abajo."""
    _par_de_firmas(c, width, y_base, "RECIBE ALIMENTOS", "ENTREGA UTENSILIOS")
    _par_de_firmas(c, width, y_base - SEP_PARES,
                   "ENTREGA ALIMENTOS", "RECIBE UTENSILIOS")


def _firma_mortera(c, width, y_recibe) -> None:
    """Par estandar arriba + seis lineas de control + par inferior."""
    _par_de_firmas(c, width, y_recibe, "RECIBE ALIMENTOS", "ENTREGA UTENSILIOS")

    # El bloque arranca 35 pt por debajo del par superior para dejar respiro.
    bloque_top = y_recibe - 35
    centro = width * COL_SIG_1
    n_firmas = len(ETIQUETAS_MORTERA)

    for i, etiqueta in enumerate(ETIQUETAS_MORTERA):
        fy = bloque_top - 10 - i * SEP_FIRMAS_MORTERA
        c.setStrokeColorRGB(0.25, 0.25, 0.25)
        c.setLineWidth(0.6)
        c.line(
            centro - ANCHO_FIRMA_MORTERA / 2, fy,
            centro + ANCHO_FIRMA_MORTERA / 2, fy,
        )
        c.setFont("Helvetica-Bold", 7)
        c.setFillColorRGB(0.1, 0.1, 0.1)

        # Ver nota de DIBUJAR_ETIQUETAS_MORTERA: el original no lo hacia.
        if DIBUJAR_ETIQUETAS_MORTERA:
            c.drawCentredString(centro, fy + 2, etiqueta)

    # Par inferior, justo debajo del bloque.
    y_entrega = (
        bloque_top - 10 - (n_firmas - 1) * SEP_FIRMAS_MORTERA
        - SEP_FIRMAS_MORTERA - 10
    )
    _par_de_firmas(c, width, y_entrega, "ENTREGA ALIMENTOS", "RECIBE UTENSILIOS")


# ── El machote completo ────────────────────────────────────────

def _pie(c, width) -> None:
    c.setFont("Helvetica-Oblique", 6)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(width / 2, 18, PIE_PAGINA)


def _comanda_standard(c, comanda: Comanda, fecha_texto: str, titulo: str) -> None:
    width, height = letter

    y = _dibujar_header(c, width, height, fecha_texto, titulo, comanda.comanda)
    y = _dibujar_observaciones(c, width, y, comanda.observaciones)
    y = _dibujar_tabla_datos(c, width, comanda, y)

    y_bajo_tablas = _dibujar_tablas_utensilios(c, width, y - 20)
    _firma_estandar(c, width, y_bajo_tablas - 50)

    _pie(c, width)


def _comanda_con_mortera(c, comanda: Comanda, fecha_texto: str, titulo: str) -> None:
    width, height = letter

    y = _dibujar_header(c, width, height, fecha_texto, titulo, comanda.comanda)
    y = _dibujar_observaciones(c, width, y, comanda.observaciones)
    y = _dibujar_tabla_datos(c, width, comanda, y)

    y_bajo_tablas = _dibujar_tablas_utensilios(c, width, y - 10)
    _firma_mortera(c, width, y_bajo_tablas - 28)

    _pie(c, width)


# ── Generadores publicos ───────────────────────────────────────

def pdf_comanda(comanda: Comanda, fecha_texto: str, titulo: str) -> bytes:
    """Una sola comanda en un PDF de una pagina."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    _comanda_standard(c, comanda, fecha_texto, titulo)
    c.save()
    return buffer.getvalue()


def pdf_comandas(comandas: list[Comanda], fecha_texto: str, titulo: str,
                 con_mortera: bool = False) -> bytes:
    """Todas las comandas, una por pagina, ordenadas por folio.

    con_mortera=True dibuja las de tipo MORTERA con las seis lineas de control
    adicionales y las demas en el diseno normal.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    ordenadas = sorted(comandas, key=lambda x: x.comanda)
    for i, comanda in enumerate(ordenadas):
        if i > 0:
            c.showPage()
        if con_mortera and comanda.tipo == 'MORTERA':
            _comanda_con_mortera(c, comanda, fecha_texto, titulo)
        else:
            _comanda_standard(c, comanda, fecha_texto, titulo)

    c.save()
    return buffer.getvalue()
