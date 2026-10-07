"""
Genera los mismos PDF con la app de Streamlit ORIGINAL y con el modulo nuevo,
para comparar texto. Es la verificacion de que el port no cambio el papel.

    python scripts/comparar_pdf.py            -> muestra el diff
    python scripts/comparar_pdf.py --guardar  -> deja los PDFs en scripts/_out/

Se ejecuta desde precarga2 pero importa la app del otro proyecto por ruta, asi
que no se copia nada: las dos implementaciones se ejecutan de verdad.
"""
import base64
import io
import math
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ORIGEN = Path(r"C:\Users\Admin\Desktop\comandas")

from pypdf import PdfReader  # noqa: E402

from core.comandas.parser import Comanda  # noqa: E402
from core.comandas.pdf import (  # noqa: E402
    pdf_comanda, pdf_comandas, pdf_comandas_mortera, pdf_vales,
    pdf_reporte_estadistico,
)

FECHA_ISO = "2026-05-13"
FECHA_TEXTO = "MARTES, 13 DE MAYO DE 2026"
TITULO = "REFORMA PEMEX"


def _c(folio, destino="PAPA LOAPAN", tipo="VIANDA", m1=10, m2=0, obs="", comp="KOL TOV"):
    """Comanda del modulo nuevo (dataclass)."""
    return Comanda(folio, "08:30", comp, destino, m1, "GANGWAY", m1, m2, tipo, obs)


def _d(folio, destino="PAPA LOAPAN", tipo="VIANDA", m1=10, m2=0, obs="", comp="KOL TOV"):
    """Misma comanda como diccionario: el formato que consume la app original."""
    return {
        "comanda": folio, "horario": "08:30", "compania": comp, "destino": destino,
        "pax": m1, "transporte": "GANGWAY", "menu_1": m1, "menu_2": m2,
        "tipo": tipo, "observaciones": obs,
    }


def _original():
    """Carga SOLO la clase ComandaApp de la app de Streamlit, sin su UI.

    Importar `app.py` entero no sirve: al importarse ejecuta codigo de interfaz
    (set_page_config, widgets, st.stop si falta configuracion) y revienta. En
    vez de eso se recorta el bloque de la clase del archivo original y se
    ejecuta en un espacio de nombres propio. Es el codigo real, no una
    reimplementacion: por eso la comparacion sirve.

    Los stubs de streamlit solo hacen falta para que los `except` de parse_pdf
    tengan donde escribir. Los generadores de PDF no los tocan.
    """
    import types

    if "streamlit" not in sys.modules:
        stub = types.ModuleType("streamlit")

        class _Sesion(dict):
            def __getattr__(self, k):
                return self.get(k)

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        stub.session_state = _Sesion()
        stub.secrets = {}
        for nombre in ("error", "warning", "info", "success", "markdow", "stop", "rerun"):
            setattr(stub, nombre, lambda *a, **k: None)
        sys.modules["streamlit"] = stub

    fuente = (ORIGEN / "app.py").read_text(encoding="utf-8")
    inicio = fuente.index("class ComandaApp:")
    fin = fuente.index("# ─────", inicio)          # fin del bloque de la clase
    clase = fuente[inicio:fin]

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Table, TableStyle
    from datetime import datetime

    espacio: dict = {
        "streamlit": sys.modules["streamlit"],
        "PdfReader": PdfReader,
        "canvas": canvas, "letter": letter, "colors": colors,
        "Table": Table, "TableStyle": TableStyle,
        "re": re, "io": io, "math": math, "datetime": datetime,
        "base64": base64,
    }

    try:
        exec(compile(clase, str(ORIGEN / "app.py"), "exec"), espacio)
    except Exception as exc:
        print(f"No se pudo cargar la clase original: {type(exc).__name__}: {exc}")
        print("Se omite la comparacion contra el original.")
        return None
    return espacio["ComandaApp"]


def _texto(pdf_bytes) -> list[str]:
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf_bytes)).pages]


def _normalizar(lineas: list[str]) -> str:
    """Quita lo que no es contenido: numeros de pagina y espacios multiples."""
    todo = "\n".join(lineas)
    todo = re.sub(r'[ \t]+', ' ', todo)
    return "\n".join(
        ln.strip() for ln in todo.splitlines()
        if ln.strip() and not re.fullmatch(r'\d+', ln.strip())
    )


def main() -> int:
    guardar = "--guardar" in sys.argv
    App = _original()

    datos = [
        _c("ABC123"), _c("DEF456", "AEREO", "MORTERA", 20, 0, "MORTERA CON 6 FIRMAS"),
        _c("GHI789", "CAYO ARCAS", "VIANDA", 5, 8),
    ]
    datos_dict = [_d("ABC123"), _d("DEF456", "AEREO", "MORTERA", 20, 0, "MORTERA CON 6 FIRMAS"),
                  _d("GHI789", "CAYO ARCAS", "VIANDA", 5, 8)]

    comparables = [
        ("comanda individual", pdf_comanda(datos[0], FECHA_TEXTO, TITULO),
         lambda a: a.generar_pdf_comanda_bytes(datos_dict[0])),
        ("todas las comandas", pdf_comandas(datos, FECHA_TEXTO, TITULO),
         lambda a: a.generar_todas_pdf_bytes()),
        ("comandas con mortera", pdf_comandas_mortera(datos, FECHA_TEXTO, TITULO),
         lambda a: a.generar_todas_mortera_pdf_bytes()),
        ("vales", pdf_vales(datos, FECHA_TEXTO),
         lambda a: a.generar_vales_pdf_bytes()),
        ("reporte estadistico", pdf_reporte_estadistico(datos, FECHA_TEXTO, TITULO),
         lambda a: a.generar_reporte_estadistico_bytes()),
    ]

    if guardar:
        out = Path(__file__).parent / "_out"
        out.mkdir(exist_ok=True)
        for nombre, nuevo, _ in comparables:
            (out / f"nuevo_{nombre.replace(' ', '_')}.pdf").write_bytes(nuevo)

    if App is None:
        print("\nSin app original: se guardaron los PDFs nuevos en scripts/_out/ para "
              "comparar a mano.")
        return 0

    app = App(username=None)
    app.fecha_pdf = FECHA_TEXTO
    app.titulo_proyecto = TITULO
    app.comandas = datos_dict

    fallos = 0
    print(f"{'caso':26} {'orig':>5} {'nuevo':>5}  resultado")
    for nombre, nuevo, generar_original in comparables:
        try:
            viejo = generar_original(app)
        except Exception as exc:
            print(f"{nombre:26} {'-':>5} {len(_texto(nuevo)):>5}  "
                  f"original fallo: {type(exc).__name__}: {exc}")
            fallos += 1
            continue

        pag_old, pag_new = _texto(viejo), _texto(nuevo)
        if len(pag_old) != len(pag_new):
            print(f"{nombre:26} {len(pag_old):>5} {len(pag_new):>5}  "
                  f"DIFIERE numero de paginas")
            fallos += 1
            continue

        diferencias = 0
        for i, (a, b) in enumerate(zip(pag_old, pag_new)):
            if _normalizar([a]) != _normalizar([b]):
                diferencias += 1
                if guardar:
                    out = Path(__file__).parent / "_out"
                    (out / f"orig_{nombre.replace(' ', '_')}_p{i + 1}.txt").write_text(
                        a, encoding="utf-8")
                    (out / f"nuevo_{nombre.replace(' ', '_')}_p{i + 1}.txt").write_text(
                        b, encoding="utf-8")
        marca = "IDENTICO" if diferencias == 0 else f"{diferencias} pag(s) difieren"
        fallos += 1 if diferencias else 0
        print(f"{nombre:26} {len(pag_old):>5} {len(pag_new):>5}  {marca}")

    print("\n" + ("PORT VERIFICADO CONTRA EL ORIGINAL"
                  if not fallos else f"{fallos} diferencia(s) — revisar en scripts/_out/"))
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
