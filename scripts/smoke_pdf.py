"""Prueba manual de humo de los 5 generadores de PDF (F1)."""
import io
import sys
from pathlib import Path

# El proyecto no esta instalado como paquete: `main.py` mete la raiz en
# sys.path al arrancar. Este script corre directo, asi que lo hace aqui.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pypdf import PdfReader

from core.comandas.parser import Comanda
from core.comandas.pdf import (
    pdf_comanda,
    pdf_comandas,
    pdf_comandas_mortera,
    pdf_reporte_estadistico,
    pdf_vales,
)

FECHA = "MARTES, 13 DE MAYO DE 2026"


def C(folio, destino="PAPA LOAPAN", tipo="VIANDA", m1=10, m2=0, obs="", comp="KOL TOV"):
    return Comanda(folio, "08:30", comp, destino, m1, "GANGWAY", m1, m2, tipo, obs)


uno = [C("ABC123")]
varios = [
    C(f"CMN{i:03d}", "PAPA LOAPAN", "MORTERA" if i % 3 == 0 else "VIANDA", 10 + i, i % 4)
    for i in range(12)
]

casos = [
    ("comanda individual", pdf_comanda(uno[0], FECHA, "REFORMA PEMEX"), 1),
    ("todas (12)", pdf_comandas(varios, FECHA, "REFORMA PEMEX"), 12),
    ("con mortera (12)", pdf_comandas_mortera(varios, FECHA, "REFORMA PEMEX"), 12),
    ("vales (12 -> 2 pag)", pdf_vales(varios, FECHA), 2),
    ("estadistico (12)", pdf_reporte_estadistico(varios, FECHA, "REFORMA PEMEX"), None),
]

fallos = 0
for nombre, data, esperado in casos:
    n = len(PdfReader(io.BytesIO(data)).pages)
    ok = esperado is None or n == esperado
    fallos += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {nombre:24} {n:2} pag  {len(data):7,} bytes")

texto = PdfReader(io.BytesIO(casos[0][1])).pages[0].extract_text()
print("\nContenido del machote:")
for token in [
    "RECIBE ALIMENTOS", "ENTREGA UTENSILIOS", "ENTREGA ALIMENTOS", "RECIBE UTENSILIOS",
    "ABC123", "CONTROL DE ENTREGA", "428224804", "KOL TOV", "SHAT", "13 DE MAYO DE 2026",
    "PORTA VIANDA", "TOTAL ARTICULOS", "NOMBRE Y FIRMA",
]:
    presente = token in texto
    fallos += 0 if presente else 1
    print(f"  {'ok   ' if presente else 'FALTA'} {token}")

mortera = PdfReader(
    io.BytesIO(pdf_comandas_mortera([C("MOR001", tipo="MORTERA")], FECHA, "T"))
).pages[0].extract_text()
etiquetas = [
    "ELABORÓ", "SUPERVISÓ", "AUTORIZÓ",
    "RECIBIÓ MORTERA", "ENTREGÓ MORTERA", "OPERADOR RESPONSABLE",
]
presentes = [e for e in etiquetas if e in mortera]
print(f"\nMortera con DIBUJAR_ETIQUETAS_MORTERA=False (papel de siempre): "
      f"{len(presentes)}/6 etiquetas visibles -> {presentes or 'ninguna, como el original'}")

# Con el interruptor en True deben aparecer las seis.
import core.comandas.pdf.comanda as mod_comanda

mod_comanda.DIBUJAR_ETIQUETAS_MORTERA = True
try:
    con_etiquetas = PdfReader(
        io.BytesIO(pdf_comandas_mortera([C("MOR001", tipo="MORTERA")], FECHA, "T"))
    ).pages[0].extract_text()
    faltan = [e for e in etiquetas if e not in con_etiquetas]
    print(f"Mortera con el interruptor en True: {6 - len(faltan)}/6 etiquetas visibles"
          + (f"  FALTAN: {faltan}" if faltan else ""))
    fallos += len(faltan)
finally:
    mod_comanda.DIBUJAR_ETIQUETAS_MORTERA = False

# Una comanda VIANDA NO debe llevar el bloque de mortera.
vianda = PdfReader(
    io.BytesIO(pdf_comandas([C("VIO001", tipo="VIANDA")], FECHA, "T"))
).pages[0].extract_text()
contaminada = [e for e in etiquetas if e in vianda]
print(f"Vianda sin contaminar con el bloque de mortera: "
      f"{'OK' if not contaminada else 'FALLA ' + str(contaminada)}")
fallos += 0 if not contaminada else 1

# 35 companias fuerza la paginacion de la tabla del reporte estadistico
muchas = [C(f"CMN{i:03d}", comp=f"COMPAÑIA NUMERO {i} S.A. DE C.V.") for i in range(35)]
paginas = len(PdfReader(io.BytesIO(pdf_reporte_estadistico(muchas, FECHA, "T"))).pages)
print(f"Reporte con 35 companias: {paginas} paginas (paginacion de la tabla)")
fallos += 0 if paginas > 1 else 1

print("\n" + ("TODO OK" if fallos == 0 else f"{fallos} FALLOS"))
raise SystemExit(1 if fallos else 0)
