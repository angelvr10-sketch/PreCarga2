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


# ── El concentrado de octubre, que hizo falta el lector por columnas ──

CONCENTRADO = "ComandaAlimentos1410.pdf"

pytestmark_oct = pytest.mark.skipif(
    not (FIXTURES / CONCENTRADO).is_file(),
    reason=f"Falta {CONCENTRADO} en {FIXTURES}",
)


@ pytestmark_oct
class TestConcentradoOctubre:
    """El reporte que motivo leer por columnas (`core/comandas/tabla.py`).

    Este PDF trae dos cosas que el aplanado de texto destruye, y las dos estan
    en el mismo archivo:

      1. `pypdf` partio el `13` de OCT047 en `1 3`. El regex tomaba el `3` como
         PAX y se perdian 10 personas: la suma daba 517 en vez de 527.
      2. Al final de cada bloque hay una fila de SUBTOTAL (`62 62 00`) y al pie
         un TOTAL. Al aplanar, esa fila se pegaba a la ultima comanda del
         bloque y dos de sus numeros caian en la columna MENU 2: 121 de comida
         que en el papel no existe.

    El PDF dice `TOTAL= 527` en su ultima linea, y estos tests dicen lo mismo.
    """

    def _parse(self):
        from core.comandas.parser import parse_pdf

        return parse_pdf((FIXTURES / CONCENTRADO).read_bytes())

    def test_el_total_es_el_del_pdf(self):
        """El total de alimentos tiene que ser el 527 que trae el reporte."""
        r = self._parse()

        assert len(r.comandas) == 52
        assert r.total_pax == 527

    def test_total_alimentos_de_la_app(self):
        """`total_alimentos` es lo que sale en pantalla: menu 1 + menu 2."""
        from core.comandas.stats import calcular_estadisticas

        s = calcular_estadisticas(self._parse().comandas)
        assert s.total_alimentos == 527

    def test_menu_2_debe_ser_cero(self):
        """Ninguna fila del reporte trae comida en MENU 2.

        Este es el que atrapa las filas de subtotal pegadas a la ultima comanda
        del bloque: si vuelve a pasar, el total se infla sin que se vea.
        """
        from core.comandas.parser import parse_pdf
        from core.comandas.stats import calcular_estadisticas

        r = parse_pdf((FIXTURES / CONCENTRADO).read_bytes())
        s = calcular_estadisticas(r.comandas)

        assert s.total_menu2 == 0, [
            f"{c.comanda}: menu_2={c.menu_2}" for c in r.comandas if c.menu_2
        ]

    def test_oct047_no_pierde_personas(self):
        """La fila que `pypdf` parti: 13 personas, no 3."""
        por_folio = {c.comanda: c for c in self._parse().comandas}

        assert por_folio["OCT047"].pax == 13
        assert por_folio["OCT047"].menu_1 == 13
        # El `1` partido tampoco puede quedarse pegado al destino.
        assert por_folio["OCT047"].destino == "ABKATUN-N1"

    def test_las_agrupaciones_reproducen_el_total(self):
        from core.comandas.stats import calcular_estadisticas

        s = calcular_estadisticas(self._parse().comandas)

        assert sum(s.por_destino.values()) == 527
        assert sum(s.por_destino_grafico.values()) == 527
        assert sum(s.por_compania.values()) == 527
        assert sum(s.por_transporte.values()) == 527
        assert s.total_mortera + s.total_viandas == 527

    def test_fecha_y_titulo(self):
        r = self._parse()
        assert r.fecha_iso == "2026-10-14"
        assert r.fecha_texto == "MIÉRCOLES, 14 DE OCTUBRE DE 2026"
        assert r.titulo == "REFORMA PEMEX"

    def test_no_advierte_folios_perdidos(self):
        r = self._parse()
        perdidas = [a for a in r.advertencias if "no se interpretaron" in a]
        assert not perdidas, perdidas

    def test_los_cuatro_reportos_dan_el_mismo_lector(self):
        """Los cuatro concentrados comparten geometria: mismo total por columna.

        Si la plataforma cambiara el layout, el lector por columnas empezaria a
        sacar otra cosa y esta comparacion lo delata.
        """
        from core.comandas.tabla import leer_tabla

        if not all((FIXTURES / a).is_file() for a in ARCHIVOS):
            pytest.skip("faltan los otros concentrados")

        for nombre, esperado in zip(ARCHIVOS, [295, 412, 449]):
            filas = leer_tabla((FIXTURES / nombre).read_bytes())
            assert sum(f.pax for f in filas) == esperado, nombre
            assert sum(f.menu_2 for f in filas) == 0, nombre

        filas = leer_tabla((FIXTURES / CONCENTRADO).read_bytes())
        assert sum(f.pax for f in filas) == 527
        assert sum(f.menu_2 for f in filas) == 0
