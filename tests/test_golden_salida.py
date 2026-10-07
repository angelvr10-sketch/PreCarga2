"""
EL TEST DEFINITIVO: el PDF que genera el modulo nuevo contra el PDF que genero
la app original.

`tests/fixtures/Todas_las_Comandas_REFORMA_PEMEX.pdf` son las 30 paginas del
machote que produjo ComandasPro el 2026-10-06: 30 comandas de REFORMA PEMEX para
el miercoles 7 de octubre de 2026, con 295 PAX en total.

No se comparan textos sueltos sino GEOMETRIA REAL DE PAGINA. De cada pagina se
saca la posicion (x, y) de cada linea, se deduce del golden la comanda que
describe, se vuelve a dibujar con el modulo nuevo y se comparan las coordenadas.

Es mas fuerte que comparar texto: si una linea de firma se mueve medio
milimetro, el texto puede seguir coincidiendo y aqui se nota.

Detalle tecnico: reportlab dibuja las tablas de `platypus` bajo una matriz de
transformacion, asi que las coordenadas del `tm` del visor de pypdf son LOCALES
a esa matriz. Hay que aplicar la CTM para obtener la posicion en la pagina.

Si el golden no esta, toda la clase se salta.
"""
import io
import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from core.comandas.parser import Comanda
from core.comandas.pdf import pdf_comandas

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GOLDEN = FIXTURES / "Todas_las_Comandas_REFORMA_PEMEX.pdf"

pytestmark = pytest.mark.skipif(
    not GOLDEN.is_file(),
    reason=f"Falta el golden {GOLDEN.name}",
)

TITULO = "REFORMA PEMEX"
FECHA = "MIÉRCOLES, 7 DE OCTUBRE DE 2026"

# Rangos x de las columnas de la tabla de datos. La tabla se dibuja con
# colWidths [100, 195, 90, 60, 60] y margen (612 - 505) / 2 = 53.5, asi que las
# columnas empiezan en 53.5, 153.5, 348.5, 438.5 y 498.5.
COL_DESTINO = (0.0, 153.5)
COL_COMPANIA = (153.5, 348.5)
COL_PAX = (348.5, 438.5)
COL_MENU1 = (438.5, 498.5)
COL_MENU2 = (498.5, 612.0)

ETIQUETAS = {
    "DESTINO", "DEPARTAMENTO/COMPAÑÍA", "NO. PERSONAS", "MENU 1", "MENU 2",
    "SALIDA", "DEVOLUCIÓN", "DESCRIPCION", "CANTIDAD", "OBSERVACIONES:",
}

# reportlab emite floats; 0.1 pt son 0.035 mm, mas fino que un pelo.
TOL = 0.1


# ── Extraccion ─────────────────────────────────────────────────

def _runs(pagina):
    """[(x_abs, y_abs, texto)] con la CTM aplicada."""
    out = []

    def visitor(text, cm, tm, fd, fs):
        t = text.strip()
        if not t:
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        out.append((round(x, 1), round(y, 1), t))

    pagina.extract_text(visitor_text=visitor)
    return out


def _lineas(items):
    """Agrupa los runs por fila, de izquierda a derecha.

    Comparar linea por linea y no fragmento por fragmento es lo que hace la
    comparacion estable: dos PDFs pueden partir el mismo texto en trozos
    distintos y aun asi dibujar la pagina identica.
    """
    filas = {}
    for x, y, t in items:
        filas.setdefault(round(y / 2.0) * 2.0, []).append((x, y, t))
    return [
        (y, " ".join(t for _, _, t in sorted(xs, key=lambda z: z[0])))
        for y, xs in sorted(filas.items(), key=lambda kv: -kv[0])
    ]


def _leer_comanda(items):
    """Deduce la comanda de una pagina por geometria.

    Las franjas verticales del machote son las mismas en las 30 paginas y se
    delimitan con dos anclas que el propio machote dibuja: 'SALIDA' y
    'NO. PERSONAS'.
    """
    y_salida = next((y for x, y, t in items if t == "SALIDA"), 0)
    y_tabla = next((y for x, y, t in items if t == "NO. PERSONAS"), 0)
    y_obs = next((y for x, y, t in items if t == "OBSERVACIONES:"), None)

    folio = fecha = titulo = ""
    observaciones = destino = compania = ""
    pax = menu_1 = menu_2 = 0

    for x, y, t in items:
        if y_salida <= y < y_tabla and t not in ETIQUETAS:
            if re.fullmatch(r'\d{1,3}', t):
                if COL_PAX[0] <= x < COL_PAX[1] and not pax:
                    pax = int(t)
                elif COL_MENU1[0] <= x < COL_MENU1[1] and not menu_1:
                    menu_1 = int(t)
                elif COL_MENU2[0] <= x < COL_MENU2[1]:
                    menu_2 = int(t)
            elif COL_DESTINO[0] <= x < COL_DESTINO[1]:
                destino = f"{destino} {t}".strip()
            elif COL_COMPANIA[0] <= x < COL_COMPANIA[1]:
                compania = f"{compania} {t}".strip()

    if y_obs is not None:
        for x, y, t in items:
            if y_tabla <= y < y_obs and not re.fullmatch(r'[A-Z]{3}\d+', t) \
                    and t not in ETIQUETAS:
                observaciones = f"{observaciones} {t}".strip()

    zona_alta = (y <= y_obs) if y_obs is not None else (y >= y_tabla)
    for x, y, t in items:
        if zona_alta:
            if re.fullmatch(r'[A-Z]{3}\d+', t) and not folio:
                folio = t
            elif re.match(r'[A-ZÁÉÍÓÚÑ]+,\s*\d{1,2}\s+DE\s', t):
                fecha = t
            elif t in ("REFORMA PEMEX", "CERRO DE LA PEZ", "ALIMENTOS AL AREA"):
                titulo = t

    return {
        "folio": folio, "fecha": fecha, "titulo": titulo,
        "destino": destino, "compania": compania,
        "pax": pax, "menu_1": menu_1, "menu_2": menu_2,
        "observaciones": observaciones,
    }


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def golden_paginas():
    return list(PdfReader(GOLDEN).pages)


@pytest.fixture(scope="module")
def golden_comandas(golden_paginas):
    comandas = []
    for pagina in golden_paginas:
        d = _leer_comanda(_runs(pagina))
        comandas.append(Comanda(
            comanda=d["folio"], horario="06:00", compania=d["compania"],
            destino=d["destino"], pax=d["pax"], transporte="GANGWAY",
            menu_1=d["menu_1"], menu_2=d["menu_2"], tipo="VIANDA",
            observaciones=d["observaciones"],
        ))
    return comandas


@pytest.fixture(scope="module")
def regenerado(golden_comandas):
    pdf = pdf_comandas(golden_comandas, FECHA, TITULO)
    return list(PdfReader(io.BytesIO(pdf)).pages)


# ── Lectura del golden ─────────────────────────────────────────

class TestLecturaDelGolden:

    def test_todas_las_paginas_tienen_folio(self, golden_comandas):
        assert len(golden_comandas) == 30
        assert all(c.comanda for c in golden_comandas)

    def test_folios_seguidos_y_sin_repetir(self, golden_comandas):
        folios = [c.comanda for c in golden_comandas]
        assert len(folios) == len(set(folios))
        assert folios == sorted(folios)
        assert folios[0] == "OCT001" and folios[-1] == "OCT030"

    def test_total_pax_del_golden(self, golden_comandas):
        assert sum(c.pax for c in golden_comandas) == 295

    def test_destinos_conocidos(self, golden_comandas):
        """Este reporte va a varios destinos, todos de la lista cerrada."""
        destinos = {c.destino for c in golden_comandas}
        assert destinos <= {
            "ABKATUN A", "IXTAL-A", "POL-A", "TARATUNICH-TE", "ABKATUN-N1",
        }, f"destinos inesperados en el golden: {destinos}"
        assert "ABKATUN A" in destinos

    def test_observaciones_se_leen(self, golden_comandas):
        # La primera comanda trae 'COMIDA-VIANDA TERMO DE AGUA'.
        assert "COMIDA-VIANDA TERMO DE AGUA" in golden_comandas[0].observaciones


# ── La comparacion que importa ─────────────────────────────────

class TestGeometriaIdenticaAlGolden:

    def test_mismas_paginas(self, golden_paginas, regenerado):
        assert len(regenerado) == len(golden_paginas) == 30

    @pytest.mark.parametrize("i", range(30))
    def test_pagina_identica(self, golden_paginas, regenerado, i):
        """Cada pagina, linea por linea, con su coordenada y su texto."""
        a = _lineas(_runs(golden_paginas[i]))
        b = _lineas(_runs(regenerado[i]))
        assert len(a) == len(b), f"pagina {i + 1}: golden {len(a)} lineas, nuevo {len(b)}"
        for j, ((ya, ta), (yb, tb)) in enumerate(zip(a, b)):
            assert ta == tb, (
                f"pagina {i + 1} linea {j + 1}:\n"
                f"  golden y={ya} {ta!r}\n"
                f"  nuevo  y={yb} {tb!r}"
            )
            assert abs(ya - yb) <= TOL, (
                f"pagina {i + 1} linea {j + 1} movida: golden y={ya}, nuevo y={yb}"
            )

    def test_encabezado_con_el_dia_de_semana_con_acento(self, golden_paginas, regenerado):
        """El dia de la semana se escribe CON acento: 'MIÉRCOLES', no 'MIERCOLES'.

        El golden imprime 'MIÉRCOLES' (app.py:358). Una version del modulo
        normalizaba a 'MIERCOLES' y habria cambiado el papel que se firma.
        """
        assert FECHA in golden_paginas[0].extract_text()
        assert "MIÉRCOLES" in golden_paginas[0].extract_text()
        assert "MIERCOLES" not in golden_paginas[0].extract_text()
        assert FECHA in regenerado[0].extract_text()
