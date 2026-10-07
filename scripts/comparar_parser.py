"""
Compara el parser NUEVO contra el `parse_pdf` de la app de Streamlit, sobre un
mismo PDF. Es la verificacion de que los regex y las limpiezas no cambiaron.

    python scripts/comparar_parser.py [ruta.pdf ...]

Sin argumentos usa los PDFs de ejemplo que se generan al vuelo con reportlab
(sinteticos pero con la forma real del reporte). Si pasas PDFs reales, compara
esos.

El PDF se tiene que producir antes: reportlab lo escribe, pypdf lo vuelve a leer
y ahi se comparan los dos resultados.
"""
import io
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from comparar_pdf import _original, ORIGEN  # noqa: E402

from core.comandas.parser import parse_pdf  # noqa: E402

FECHA_PDF = "MARTES, 13 DE MAYO DE 2026"


# ── Generar un PDF de aspecto parecido al reporte ──────────────

def _pdf_de_ejemplo() -> bytes:
    """Arma un PDF minimo con la estructura que el parser busca.

    No busca ser identico al reporte real (no hay PDFs de la plataforma a mano
    todavia), sino tener la forma: folio, hora, compania, destino conocido,
    pax, transporte, menu 1, menu 2 y una linea de observaciones con MORTERA.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 720

    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y, "REFORMA PEMEX")
    c.setFont("Helvetica", 10)
    c.drawString(60, y - 20, f"CONTROL DE ENTREGA DE ALIMENTOS AL AREA DEL DIA: {FECHA_PDF}")
    y -= 60

    filas = [
        ("ABC123", "08:30", "KOL TOV", "PAPA LOAPAN", "10", "GANGWAY", "10", "0", "MORTERA CON 6 FIRMAS ADICIONALES"),
        # MARÍTIMO va CON acento: el regex de transporte lo exige asi (el
        # original también). Ver la nota de fragilidad en PLAN_COMANDAS.md.
        ("DEF456", "09:15", "SHAT", "CAYO ARCAS", "25", "MARÍTIMO", "25", "8", ""),
        ("GHI789", "10:00", "DEPARTAMENTO OPERACIONES API", "AEREO", "6", "AEREO", "6", "0", "CANASTILLA"),
        ("JKL012", "11:30", "COLONIAL MARINE", "PAPA LOAPAN", "15", "CANASTILLA", "15", "4", ""),
    ]
    c.setFont("Helvetica", 8)
    for folio, hora, comp, destino, pax, transp, m1, m2, obs in filas:
        c.drawString(40, y, f"{folio}  {hora}  {comp}  {destino}  {pax}  {transp}  {m1}  {m2}")
        if obs:
            c.drawString(40, y - 12, f"NO. COM. OBSERVACIONES: {obs}")
            y -= 12
        y -= 22

    c.save()
    return buffer.getvalue()


def _sin_noise(resultado) -> dict:
    """Compara solo el contenido, sin el titulo que depende del archivo."""
    return {
        "fecha_iso": resultado["fecha_iso"],
        "titulo": resultado["titulo"],
        "comandas": sorted(resultado["comandas"], key=lambda x: x["comanda"]),
    }


def main() -> int:
    rutas = [Path(a) for a in sys.argv[1:]]
    if not rutas:
        print("Sin PDFs reales: se compara con un PDF sintetico de ejemplo.\n")
        casos = [("ejemplo sintetico", _pdf_de_ejemplo())]
    else:
        casos = [(r.name, r.read_bytes()) for r in rutas]

    App = _original()
    if App is None:
        return 1

    original = App(username=None)
    # La app original guarda cada comanda en Supabase al parsear. Aqui no hay
    # nada que guardar: se neutraliza la escritura para no tocar datos reales y
    # el resto del parseo corre igual.
    original._save_to_db = lambda *a, **k: None

    fallos = 0
    for nombre, pdf_bytes in casos:
        print(f"-- {nombre}")

        # Nuevo
        try:
            nuevo = parse_pdf(pdf_bytes)
        except Exception as exc:
            print(f"   NUEVO fallo: {type(exc).__name__}: {exc}")
            fallos += 1
            continue

        # Original. parse_pdf devuelve self.comandas y hace merge con lo que ya
        # habia, asi que se parte de una lista vacia en cada corrida.
        original.comandas = []
        original.fecha_pdf = ""
        try:
            viejo = original.parse_pdf(pdf_bytes)
        except Exception as exc:
            print(f"   ORIGINAL fallo: {type(exc).__name__}: {exc}")
            fallos += 1
            continue

        mine = [c.a_dict() for c in nuevo.comandas]
        suyo = [dict(c) for c in viejo]
        mine.sort(key=lambda x: x["comanda"])
        suyo.sort(key=lambda x: x["comanda"])

        iguales = mine == suyo
        print(f"   {'IDENTICO' if iguales else 'DIFIERE'}  "
              f"nuevo={len(mine)}  original={len(suyo)}")
        print(f"   fecha: nuevo='{nuevo.fecha_texto}'  original='{original.fecha_pdf}'")
        print(f"   titulo: nuevo='{nuevo.titulo}'  original='{original.titulo_proyecto}'")

        if not iguales:
            fallos += 1
            por_folio = {c["comanda"]: c for c in suyo}
            for mio in mine:
                su = por_folio.get(mio["comanda"])
                if su is None:
                    print(f"     FALTA en el original: {mio['comanda']}")
                    continue
                for campo in mio:
                    if mio[campo] != su.get(campo):
                        print(f"     {mio['comanda']}.{campo}: "
                              f"nuevo={mio[campo]!r}  original={su.get(campo)!r}")
            faltantes = {c["comanda"] for c in suyo} - {m["comanda"] for m in mine}
            if faltantes:
                print(f"     FALTAN en el nuevo: {sorted(faltantes)}")

        if not mine:
            print("   sin comandas: el parser no encontro nada")
            fallos += 1
            continue

        for c in mine:
            print(f"     {c['comanda']}  {c['horario']}  {c['compania'][:26]:26}  "
                  f"{c['destino'][:16]:16}  pax={c['pax']:>3}  {c['transporte']:11}  "
                  f"m1={c['menu_1']:>3} m2={c['menu_2']:>3}  {c['tipo']}")
            if c["observaciones"]:
                print(f"          obs: {c['observaciones']}")
        print()

    print("\n" + ("PARSER OK" if not fallos else f"{fallos} fallo(s)"))
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
