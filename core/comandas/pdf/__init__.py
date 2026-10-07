"""
core/comandas/pdf/ — Los cuatro generadores de PDF.

    comanda.py      El machote de una comanda (firmas, utensilios, folio).
    vales.py        Vales de alimentos, 10 por hoja.
    estadistico.py  Reporte de una hoja con donut, barras y tabla.

Cada modulo es una funcion pura: recibe datos y devuelve bytes. Nada aqui sabe
de Supabase, de FastAPI ni de quien pidio el PDF. Eso permite probarlos con
`bytes` y nada mas.
"""

from core.comandas.pdf.comanda import pdf_comanda, pdf_comandas
from core.comandas.pdf.vales import pdf_vales
from core.comandas.pdf.estadistico import pdf_reporte_estadistico

__all__ = [
    "pdf_comanda",
    "pdf_comandas",
    "pdf_comandas_mortera",
    "pdf_vales",
    "pdf_reporte_estadistico",
]


def pdf_comandas_mortera(comandas, fecha_texto: str, titulo: str) -> bytes:
    """Atajo: el PDF de todas las comandas con las de tipo MORTERA ampliadas."""
    return pdf_comandas(comandas, fecha_texto, titulo, con_mortera=True)
