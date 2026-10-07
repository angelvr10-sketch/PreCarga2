"""
La prueba que mas importa: el modulo nuevo contra la app de Streamlit original.

Si la app vieja esta en disco, se ejecuta su clase `ComandaApp` de verdad y se
comparan sus PDF y su parseo con los del modulo nuevo, sobre el texto extraido.
Si no esta, los tests se saltan con un aviso: en otra maquina no se puede correr
la app vieja.

Es la unica forma de garantizar que el port no cambio el papel que se firma ni
los regex que leen el reporte.
"""
import io
import re
import sys
from pathlib import Path

import pytest

ORIGEN = Path(r"C:\Users\Admin\Desktop\comandas\app.py")

# Los tests que comparan contra el original usan los scripts de apoyo, que
# generan el PDF de ejemplo y cargan la clase vieja.
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

pytestmark = pytest.mark.skipif(
    not ORIGEN.is_file(),
    reason=f"La app original no esta en {ORIGEN.parent}",
)

FECHA = "MARTES, 13 DE MAYO DE 2026"
TITULO = "REFORMA PEMEX"


# ── Cargar la clase original sin su interfaz ───────────────────

def _cargar_original():
    """Ejecuta solo la clase ComandaApp del archivo original.

    Importar `app.py` entero no sirve: al importarse corre codigo de interfaz
    (set_page_config, widgets, st.stop) y revienta. Se recorta el bloque de la
    clase y se ejecuta en un espacio de nombres propio.
    """
    import base64
    import types
    from datetime import datetime

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
        for nombre in ("error", "warning", "info", "success", "markdown",
                       "stop", "rerun"):
            setattr(stub, nombre, lambda *a, **k: None)
        sys.modules["streamlit"] = stub

    from pypdf import PdfReader
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Table, TableStyle

    fuente = ORIGEN.read_text(encoding="utf-8")
    inicio = fuente.index("class ComandaApp:")

    # El final de la clase se localiza por un marcador ASCII del propio codigo
    # de la app, no por la linea decorativa de guiones (esos son U+2500 y este
    # archivo ya se ha leido con la codificacion equivocada mas de una vez).
    # "# Session State" es el comentario que abre la seccion de UI, ya fuera de
    # la clase.
    fin = fuente.index("# Session State", inicio)
    clase = fuente[inicio:fin]

    espacio = {
        "streamlit": sys.modules["streamlit"],
        "PdfReader": PdfReader, "canvas": canvas, "letter": letter,
        "colors": colors, "Table": Table, "TableStyle": TableStyle,
        "re": re, "io": io, "math": __import__("math"),
        "datetime": datetime, "base64": base64,
    }
    exec(compile(clase, str(ORIGEN), "exec"), espacio)
    return espacio["ComandaApp"]


@pytest.fixture(scope="module")
def original():
    return _cargar_original()


@pytest.fixture
def app(original):
    """ComandaApp sin conexion: se anula la escritura a Supabase."""
    instancia = original(username=None)
    instancia._save_to_db = lambda *a, **k: None
    instancia.comandas = []
    instancia.fecha_pdf = ""
    return instancia


# ── Utilidades ─────────────────────────────────────────────────

def _comanda(folio, destino="PAPALOAPAN", tipo="VIANDA", m1=10, m2=0,
             obs="", comp="KOL TOV"):
    return {
        "comanda": folio, "horario": "08:30", "compania": comp, "destino": destino,
        "pax": m1, "transporte": "GANGWAY", "menu_1": m1, "menu_2": m2,
        "tipo": tipo, "observaciones": obs,
    }


def _texto(pdf_bytes):
    from pypdf import PdfReader
    return [p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf_bytes)).pages]


def _normalizar(linea):
    """Quita espacios multiples y numeros de pagina sueltos."""
    linea = re.sub(r'[ \t]+', ' ', linea)
    return "\n".join(
        ln.strip() for ln in linea.splitlines()
        if ln.strip() and not re.fullmatch(r'\d+', ln.strip())
    )


# ── PDF: deben salir identicos ─────────────────────────────────

class TestPdfIdenticoAlOriginal:

    @pytest.mark.parametrize("nombre", [
        "comanda individual", "todas", "mortera", "vales", "estadistico",
    ])
    def test_pagina_por_pagina(self, app, varias_comandas, nombre):
        from core.comandas.pdf import (
            pdf_comanda, pdf_comandas, pdf_comandas_mortera,
            pdf_reporte_estadistico, pdf_vales,
        )

        datos_dict = [c.a_dict() for c in varias_comandas]
        app.comandas = datos_dict
        app.fecha_pdf = FECHA
        app.titulo_proyecto = TITULO

        generadores = {
            "comanda individual": (
                pdf_comanda(varias_comandas[0], FECHA, TITULO),
                lambda: app.generar_pdf_comanda_bytes(datos_dict[0]),
            ),
            "todas": (
                pdf_comandas(varias_comandas, FECHA, TITULO),
                lambda: app.generar_todas_pdf_bytes(),
            ),
            "mortera": (
                pdf_comandas_mortera(varias_comandas, FECHA, TITULO),
                lambda: app.generar_todas_mortera_pdf_bytes(),
            ),
            "vales": (
                pdf_vales(varias_comandas, FECHA),
                lambda: app.generar_vales_pdf_bytes(),
            ),
            "estadistico": (
                pdf_reporte_estadistico(varias_comandas, FECHA, TITULO),
                lambda: app.generar_reporte_estadistico_bytes(),
            ),
        }

        nuevo, hacer_original = generadores[nombre]
        viejo = hacer_original()

        paginas_nuevas = _texto(nuevo)
        paginas_viejas = _texto(viejo)

        assert len(paginas_nuevas) == len(paginas_viejas), (
            f"{nombre}: {len(paginas_viejas)} paginas antes, "
            f"{len(paginas_nuevas)} ahora"
        )
        for i, (a, b) in enumerate(zip(paginas_viejas, paginas_nuevas)):
            assert _normalizar(a) == _normalizar(b), f"{nombre} pagina {i + 1} difiere"


# ── Parser: deben coincidir comanda por comanda ────────────────

class TestParserIgualAlOriginal:

    def test_parseo_igual(self, app):
        from core.comandas.parser import parse_pdf
        from comparar_parser import _pdf_de_ejemplo

        pdf = _pdf_de_ejemplo()
        app.comandas = []
        viejo = app.parse_pdf(pdf)
        nuevo = parse_pdf(pdf)

        mio = sorted((c.a_dict() for c in nuevo.comandas), key=lambda x: x["comanda"])
        suyo = sorted((dict(c) for c in viejo), key=lambda x: x["comanda"])
        assert mio == suyo

    def test_fecha_en_espanol_no_ingles(self, app):
        # El original caia en `strftime("%B")` y escribía el mes en el idioma
        # del sistema (app.py:433). Este test fija que ya no pasa.
        from core.comandas.parser import parse_pdf
        from comparar_parser import _pdf_de_ejemplo

        app.comandas = []
        app.fecha_pdf = ""
        app.parse_pdf(_pdf_de_ejemplo())
        nuevo = parse_pdf(_pdf_de_ejemplo())

        assert nuevo.fecha_texto == "MIÉRCOLES, 13 DE MAYO DE 2026"
        assert "OCTOBER" not in nuevo.fecha_texto
        assert "MAYO" in nuevo.fecha_texto

    def test_el_dia_de_semana_lleva_acento(self, app):
        """El machote escribe 'MIÉRCOLES', con acento (app.py:358).

        El golden de salida lo confirma pagina a pagina: en las 30 paginas de
        Todas_las_Comandas_REFORMA_PEMEX.pdf dice 'MIÉRCOLES, 7 DE OCTUBRE DE
        2026'. Una version del modulo lo escribia sin acento y habria cambiado
        el papel que se firma.
        """
        from datetime import date
        from core.comandas.fecha import fecha_largo_es

        assert fecha_largo_es(date(2026, 10, 7)) == "MIÉRCOLES, 7 DE OCTUBRE DE 2026"
        assert fecha_largo_es(date(2026, 10, 10)) == "SÁBADO, 10 DE OCTUBRE DE 2026"
