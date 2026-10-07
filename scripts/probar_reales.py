"""
Parser contra los PDF REALES de la plataforma.

Estos tres archivos son los REPORTES DE ENTRADA: los que sube un usuario y de
los que la app extrae las comandas. Son el caso de uso principal.

Sirven para responder lo que ningun test sintetico puede: ¿los regex leen bien
un PDF de verdad? En concreto, ¿reconocen los nombres de destino cortos que usa
la plataforma (KU-A, YKN, MALOOB-B)?

    python scripts/probar_reales.py --detalle
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from pypdf import PdfReader  # noqa: E402

from core.comandas.parser import (  # noqa: E402
    texto_del_pdf, RE_COMANDA, DESTINO_PATTERN,
)

DESCARGAS = Path.home() / "Downloads"
ARCHIVOS = ["ComandaAlimentos.pdf", "ComandaAlimentos(1).pdf", "ComandaAlimentos(2).pdf"]


def comprobar_destinos() -> int:
    """¿Estan en la lista todos los destinos que usan las tablas?"""
    muestras = ["YKN", "KU-A", "KU-M", "KU-S", "KU-H", "MALOOB-B", "MALOOB-E",
                "MALOOB-I", "MALOOB-C", "AYATSIL-B", "ZAAP-A", "EK-A"]
    faltan = []
    print("Destinos de la plataforma contra el patron del parser:")
    for d in muestras:
        patron = rf"{DESTINO_PATTERN}\s+\d{{1,3}}\s+(?:AEREO|GANGWAY|MARÍTIMO|VIUDA|CANASTILLA)"
        ok = bool(re.search(patron, f"COMPANIA {d} 05 AEREO 05 00"))
        if not ok:
            faltan.append(d)
        print(f"  {d:12} {'OK' if ok else 'NO ESTA EN LA LISTA'}")
    return len(faltan)


def main() -> int:
    detalle = "--detalle" in sys.argv

    print(f"Destinos que reconoce el regex: {len(DESTINO_PATTERN.split('|'))} formas\n")
    faltan = comprobar_destinos()

    total = 0
    for nombre in ARCHIVOS:
        ruta = DESCARGAS / nombre
        if not ruta.is_file():
            print(f"[falta] {ruta}")
            continue

        texto = texto_del_pdf(ruta.read_bytes())
        matches = list(RE_COMANDA.finditer(texto))
        total += len(matches)

        print("\n" + "=" * 72)
        print(f"{nombre}  ({len(PdfReader(ruta).pages)} paginas)")
        print("=" * 72)
        print(f"  coincidencias RE_COMANDA: {len(matches)}")

        if detalle:
            for i, m in enumerate(matches):
                print(f"   {i + 1:3}. {m.group('comanda'):8} {m.group('horario'):6} "
                      f"{m.group('compania')[:24]:24} {m.group('destino')[:16]:16} "
                      f"pax={m.group('pax'):>4} {m.group('transporte'):10} "
                      f"m1={m.group('m1'):>4} m2={m.group('m2'):>3}")
        else:
            folios = sorted({m.group('comanda') for m in matches})
            print(f"  folios unicos: {len(folios)} -> {', '.join(folios[:8])}"
                  + (" ..." if len(folios) > 8 else ""))
            comps = sorted({m.group('compania').strip() for m in matches})
            dests = sorted({m.group('destino').strip() for m in matches})
            print(f"  companias: {', '.join(comps[:8])}"
                  + (" ..." if len(comps) > 8 else ""))
            print(f"  destinos:  {', '.join(dests)}")

    print(f"\nTotal de coincidencias en los tres archivos: {total}")
    if faltan:
        print(f"DESTINOS QUE FALTAN EN EL PATRON: {faltan}")
    return 1 if faltan or total == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
