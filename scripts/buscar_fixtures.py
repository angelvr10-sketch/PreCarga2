"""
Busca en una carpeta los PDF que tienen forma de reporte de comandas.

    python scripts/buscar_fixtures.py [carpeta] [profundidad]

Un reporte de comandas tiene: un folio tipo 'UHF123' o 'ABC123' seguido de
hora, compania, un destino de la lista, pax y un modo de transporte. Se busca
eso y no el nombre del archivo, porque los archivos estan mal nombrados.

Imprime los que pasan el filtro para poder meterlos de golden set.
"""
import logging
import re
import sys
from pathlib import Path

from pypdf import PdfReader

# Hay PDFs en el disco con diccionarios mal formados ("Multiple definitions in
# dictionary"). pypdf avisa por stderr y el script recorre cientos de archivos:
# el ruido tapa el resultado.
logging.getLogger("pypdf").setLevel(logging.ERROR)

# Solo se mira la primera pagina: los folios van en la primera tabla.
FOLIO = re.compile(r'\b[A-Z]{3}\d{2,6}\s+\d{2}:\d{2}\b')
TRANSPORTE = re.compile(r'\bAEREO|GANGWAY|MARÍTIMO|VIUDA|CANASTILLA\b')


def revisar(ruta: Path):
    """(folios distintos, muestra de texto) si parece reporte; None si no."""
    try:
        texto = PdfReader(ruta).pages[0].extract_text() or ""
    except Exception:
        return None
    if not FOLIO.search(texto) or not TRANSPORTE.search(texto):
        return None
    return len(set(FOLIO.findall(texto))), " ".join(texto.split())[:110]


def main() -> int:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"C:\Users\Admin\Desktop")
    max_prof = int(sys.argv[2]) if len(sys.argv) > 2 else 4

    if not base.is_dir():
        print(f"No existe: {base}")
        return 1

    encontrados = []
    for ruta in base.rglob("*.pdf"):
        try:
            prof = len(ruta.relative_to(base).parts) - 1
        except ValueError:
            continue
        if prof > max_prof:
            continue
        s = str(ruta).lower()
        if "node_modules" in s or "\\.venv\\" in s or "scripts\\_out" in s:
            continue
        r = revisar(ruta)
        if r:
            n, muestra = r
            encontrados.append((n, ruta, muestra))

    if not encontrados:
        print(f"Ningun PDF con forma de reporte de comandas bajo {base} "
              f"(profundidad {max_prof}).")
        return 0

    encontrados.sort(reverse=True)
    print(f"{len(encontrados)} PDF(s) con forma de reporte de comandas:\n")
    for n, ruta, muestra in encontrados:
        print(f"  {n:3} folios  {ruta}")
        print(f"              {muestra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
