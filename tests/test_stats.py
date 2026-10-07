"""Agregaciones del dashboard y del reporte estadistico."""
from core.comandas.stats import calcular_estadisticas


class TestTotales:
    def test_vacio_no_rompe(self):
        s = calcular_estadisticas([])
        assert s.total_comandas == 0
        assert s.total_alimentos == 0
        assert s.por_destino == {}

    def test_suma_pax(self, varias_comandas):
        s = calcular_estadisticas(varias_comandas)
        # `total_alimentos` es menu_1 + menu_2, no la columna `pax`: son cosas
        # distintas aunque en un PDF bien formado coincidan.
        esperado = sum(c.menu_1 + c.menu_2 for c in varias_comandas)
        assert s.total_alimentos == esperado
        assert s.total_comandas == 12

    def test_menu1_mas_menu2_da_el_total(self, varias_comandas):
        s = calcular_estadisticas(varias_comandas)
        assert s.total_alimentos == s.total_menu1 + s.total_menu2

    def test_mortera_y_vianda_parten_el_total(self, varias_comandas):
        s = calcular_estadisticas(varias_comandas)
        assert s.total_mortera + s.total_viandas == s.total_alimentos


class TestAgrupaciones:
    def test_aereos_se_agrupan_sin_destino(self, comanda):
        s = calcular_estadisticas([comanda(transporte="AEREO", destino="", menu_1=5)])
        assert "AÉREOS" in s.por_destino

    def test_gangway_se_abrevia_en_la_grafica(self, comanda):
        s = calcular_estadisticas([comanda(transporte="GANGWAY", destino="PAPA LOAPAN", menu_1=10)])
        assert "PAPA LOAPAN (GANGWAY)" in s.por_destino      # tabla: completo
        assert "PAPA LOAPAN (G)" in s.por_destino_grafico   # grafica: abreviado

    def test_maritimo_se_abrevia_en_la_grafica(self, comanda):
        s = calcular_estadisticas([comanda(transporte="MARÍTIMO", destino="CAYO ARCAS", menu_1=10)])
        assert "CAYO ARCAS (MARÍTIMO)" in s.por_destino
        assert "CAYO ARCAS (M)" in s.por_destino_grafico

    def test_canastilla_conserva_el_destino(self, comanda):
        s = calcular_estadisticas([comanda(transporte="CANASTILLA", destino="TUXPANAPA", menu_1=10)])
        assert "TUXPANAPA (CANASTILLA)" in s.por_destino
        assert "TUXPANAPA (C)" in s.por_destino_grafico

    def test_destino_vacio_no_crea_clave_vacia(self, comanda):
        # Una clave "" en la leyenda del donut se ve como un corte raro.
        s = calcular_estadisticas([comanda(destino="", menu_1=3)])
        assert "" not in s.por_destino

    def test_acepta_diccionarios_de_la_base(self, varias_comandas):
        # La base devuelve dicts envueltos, no dataclasses: ambas rutas deben
        # dar el mismo resultado.
        from_dicts = calcular_estadisticas([c.a_dict() for c in varias_comandas])
        from_dataclass = calcular_estadisticas(varias_comandas)
        assert from_dicts.a_dict() == from_dataclass.a_dict()

    def test_serializable(self, varias_comandas):
        import json
        json.dumps(calcular_estadisticas(varias_comandas).a_dict())
