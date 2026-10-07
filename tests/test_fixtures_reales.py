"""
Parser contra los PDF REALES de la plataforma.

Los tres archivos de tests/fixtures/ son los REPORTES DE ENTRADA: los que sube
un usuario y de los que la app saca las comandas. Son el caso de uso principal
del parser, no un caso secundario.

Confirma la forma real del reporte: la tabla con las columnas
`NO. COM. / HORARIO / DEPARTAMENTO-COMPAÑÍA / DESTINO / No. PAX / TRANSPORTE /
MENU 1 / MENU 2 / CUSTODIO / OBSERVACIONES`, con un campo por linea, y un pie
con la fecha en minusculas (`viernes, 3 de julio de 2026`), el proyecto
(`CERRO DE LA PEZ`) y el contrato.

Si los archivos no estan (no se versionan: son documentos operativos), toda la
clase se salta.
"""
from pathlib import Path

import pytest

from core.comandas.parser import DESTINO_PATTERN, RE_COMANDA, texto_del_pdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ARCHIVOS = ["ComandaAlimentos.pdf", "ComandaAlimentos(1).pdf", "ComandaAlimentos(2).pdf"]

pytestmark = pytest.mark.skipif(
    not all((FIXTURES / a).is_file() for a in ARCHIVOS),
    reason=f"Faltan los PDF reales en {FIXTURES}",
)


def _texto(nombre):
    return texto_del_pdf((FIXTURES / nombre).read_bytes())


# ── Destinos ───────────────────────────────────────────────────

@pytest.mark.parametrize("destino", [
    "YKN", "KU-A", "KU-M", "KU-S", "KU-H",
    "MALOOB-A", "MALOOB-B", "MALOOB-C", "MALOOB-E", "MALOOB-I",
    "AYATSIL-A", "AYATSIL-B", "AYATSIL-D", "ZAAP-A", "ZAAP-C", "EK-A",
])
def test_destinos_de_la_plataforma_estan_en_la_lista(destino):
    """La lista es cerrada: un destino que falte hace que la comanda no se vea.

    Este test es el que avisa si la plataforma empieza a usar un destino nuevo.
    """
    import re
    patron = rf"{DESTINO_PATTERN}\s+\d{{1,3}}\s+(?:AEREO|GANGWAY|MARÍTIMO|VIUDA|CANASTILLA)"
    assert re.search(patron, f"COMPANIA {destino} 05 AEREO 05 00"), (
        f"El destino '{destino}' no esta en DESTINO_PATTERN: sus comandas no se "
        f"detectaran. Agregarlo a core/comandas/parser.py."
    )


# ── Lectura completa ───────────────────────────────────────────

class TestPdfReales:

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_encuentra_comandas(self, nombre):
        matches = list(RE_COMANDA.finditer(_texto(nombre)))
        assert len(matches) > 0, f"{nombre}: el regex no encontro ninguna comanda"

    @pytest.mark.parametrize("nombre,esperado", [
        ("ComandaAlimentos.pdf", 18),
        ("ComandaAlimentos(1).pdf", 48),
        ("ComandaAlimentos(2).pdf", 47),
    ])
    def test_cantidad_de_comandas(self, nombre, esperado):
        """Numero congelado el 2026-10-06 contra los PDF de la plataforma.

        Si esto falla, el parser cambio de comportamiento. O cambio el PDF (y hay
        que revisar el reporte nuevo a proposito), o se rompio algo en el regex.
        """
        assert len(list(RE_COMANDA.finditer(_texto(nombre)))) == esperado

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_folios_sin_duplicar(self, nombre):
        """Cada folio debe aparecer una vez. Un folio repetido significa que el
        parser se comio dos filas."""
        folios = [m.group('comanda') for m in RE_COMANDA.finditer(_texto(nombre))]
        assert len(folios) == len(set(folios))

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_formato_de_folio_de_la_plataforma(self, nombre):
        """Los folios reales son MES + 3 digitos: JUL025, AGO041, SEP021.

        Es la validacion directa del grupo `comanda` del regex contra los datos
        de verdad, no contra lo que uno supone.
        """
        import re
        for m in RE_COMANDA.finditer(_texto(nombre)):
            assert re.fullmatch(r'[A-Z]{3}\d{3}', m.group('comanda')), \
                f"{nombre}: folio con formato inesperado {m.group('comanda')!r}"

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_horarios_validos(self, nombre):
        """HH:MM de verdad. Un horario raro indica que el regex se desalineo y
        esta leyendo de otra columna."""
        import re
        for m in RE_COMANDA.finditer(_texto(nombre)):
            assert re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', m.group('horario')), \
                f"{nombre}: horario invalido {m.group('horario')!r} en {m.group('comanda')}"

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_transportes_validos(self, nombre):
        for m in RE_COMANDA.finditer(_texto(nombre)):
            assert m.group('transporte') in {"AEREO", "GANGWAY", "MARÍTIMO",
                                             "VIUDA", "CANASTILLA"}, \
                f"{nombre}: transporte raro {m.group('transporte')!r}"

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_puede_haber_discrepancia_entre_pax_y_menu1(self, nombre):
        """Los reportes reales traen comandas donde PAX y MENU 1 no coinciden.

        Casos conocidos: JUL026 (pax 125, menu1 126) y SEP014 (pax 04, menu1 05).
        Por eso el parser pone `menu_1 = pax` y descarta la columna del reporte:
        el conteo de comida sale de las personas, no de lo que diga la columna de
        menu. Este test deja constancia de que la discrepancia es real en los
        datos de la plataforma, y el de abajo fija que la regla se aplica.
        """
        discrepancias = [
            (m.group('comanda'), m.group('pax'), m.group('m1'))
            for m in RE_COMANDA.finditer(_texto(nombre))
            if m.group('m1') != m.group('pax')
        ]
        for folio, pax, menu1 in discrepancias:
            assert pax and menu1, f"{folio}: valores vacios pax={pax} menu1={menu1}"
        if discrepancias:
            print(f"\n  {nombre}: {len(discrepancias)} comanda(s) con PAX != MENU 1 "
                  f"-> {discrepancias[:5]}")

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_el_parser_usa_pax_como_menu_1(self, nombre):
        """Regla deliberada: `menu_1` siempre vale `pax`, nunca la columna del PDF."""
        from core.comandas.parser import comandas_del_texto

        for c in comandas_del_texto(_texto(nombre)):
            assert c.menu_1 == c.pax, (
                f"{nombre}: en {c.comanda} menu_1={c.menu_1} pero pax={c.pax}; "
                f"la regla es menu_1 = pax"
            )

    def test_lectura_completa_de_una_comanda(self):
        """Comprobacion punto por punto de una comanda concreta, para que un
        falloFuture diga exactamente que campo se rompio."""
        matches = {m.group('comanda'): m for m in RE_COMANDA.finditer(_texto(ARCHIVOS[0]))}

        m = matches["JUL025"]
        assert m.group('horario') == "06:00"
        assert m.group('compania').strip() == "PEMEX"
        assert m.group('destino').strip() == "YKN"
        assert m.group('pax') == "02"
        assert m.group('transporte') == "AEREO"
        assert m.group('m1') == "02"
        assert m.group('m2') == "00"

    def test_comanda_con_mas_de_100_pax(self):
        """Hay comandas de 125 personas: el pax es de tres digitos.

        Y es justamente una de las que tiene discrepancia con menu 1 (126), lo
        que confirma que el parser la lee bien y despues aplica la regla.
        """
        matches = {m.group('comanda'): m for m in RE_COMANDA.finditer(_texto(ARCHIVOS[0]))}
        assert "JUL026" in matches
        assert matches["JUL026"].group('pax') == "125"
        assert matches["JUL026"].group('m1') == "126"   # la columna del PDF, sin corregir


class TestPipelineCompleto:
    """`parse_pdf` de punta a punta sobre los reportes de entrada reales.

    Este es el caso de uso real: el usuario sube el reporte y la app guarda lo
    que sale de aqui. Si estos tests pasan, el parser lee la plataforma.
    """

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_no_advierte_folios_perdidos(self, nombre):
        """Ninguno de los tres pierde folios.

        Este test existio porque la columna de observaciones trae 'MENU1-VIANDA'
        y el detector de folios lo leia como una comanda llamada 'ENU1':
        reportaba una perdida que no existia. Si vuelve a pasar, este test falla.
        """
        from core.comandas.parser import parse_pdf

        r = parse_pdf((FIXTURES / nombre).read_bytes())
        perdidas = [a for a in r.advertencias if "no se interpretaron" in a]
        assert not perdidas, f"{nombre}: {perdidas}"

    @pytest.mark.parametrize("nombre,fecha_iso,titulo", [
        ("ComandaAlimentos.pdf", "2026-07-03", "CERRO DE LA PEZ"),
        ("ComandaAlimentos(1).pdf", "2026-08-14", "CERRO DE LA PEZ"),
        ("ComandaAlimentos(2).pdf", "2026-09-01", "CERRO DE LA PEZ"),
    ])
    def test_fecha_y_titulo(self, nombre, fecha_iso, titulo):
        """La fecha del PDF se lee y se guarda como ISO. Es la llave por la que
        despues se agrupan las comandas en el dashboard."""
        from core.comandas.parser import parse_pdf

        r = parse_pdf((FIXTURES / nombre).read_bytes())
        assert r.fecha_iso == fecha_iso
        assert r.titulo == titulo

    @pytest.mark.parametrize("nombre", ARCHIVOS)
    def test_mes_en_espanol(self, nombre):
        """Ninguna fecha puede llevar un mes en ingles."""
        from core.comandas.parser import parse_pdf

        r = parse_pdf((FIXTURES / nombre).read_bytes())
        assert "OCTOBER" not in r.fecha_texto.upper()
        assert "FEBRUARY" not in r.fecha_texto.upper()
        assert "SEPTEMBER" not in r.fecha_texto.upper()

    @pytest.mark.parametrize("nombre,comandas,pax", [
        ("ComandaAlimentos.pdf", 18, 295),
        ("ComandaAlimentos(1).pdf", 48, 412),
        ("ComandaAlimentos(2).pdf", 47, 449),
    ])
    def test_totales_coherentes(self, nombre, comandas, pax):
        """El total de PAX del reporte tiene que coincidir con la suma por
        destino: si no cuadran, el dashboard y el PDF saldrian distintos."""
        from core.comandas.parser import parse_pdf
        from core.comandas.stats import calcular_estadisticas

        r = parse_pdf((FIXTURES / nombre).read_bytes())
        s = calcular_estadisticas(r.comandas)

        assert len(r.comandas) == comandas
        assert r.total_pax == pax
        assert s.total_alimentos == pax
        # La suma de cada agrupacion debe reproducir el total.
        assert sum(s.por_destino.values()) == pax
        assert sum(s.por_destino_grafico.values()) == pax
        assert sum(s.por_compania.values()) == pax
        assert sum(s.por_transporte.values()) == pax
        assert s.total_mortera + s.total_viandas == pax
