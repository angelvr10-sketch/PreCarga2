"""
Tests del parser.

La parte importante: el parser se compara contra la app de Streamlit original
para garantizar que los regex no cambiaron. Eso vive en
`test_comparar_original.py`, que necesita el otro proyecto en disco.

Aqui se cubren los bordes del parser aislado.
"""
import pytest

from core.comandas.parser import (
    Comanda,
    ErrorProcesandoPDF,
    comandas_del_texto,
    observaciones_por_folio,
    texto_del_pdf,
    titulo_del_pdf,
)


class TestErrores:
    def test_basura_no_es_pdf(self):
        with pytest.raises(ErrorProcesandoPDF):
            texto_del_pdf(b"esto no es un pdf")

    def test_vacio(self):
        with pytest.raises(ErrorProcesandoPDF):
            texto_del_pdf(b"")


class TestTitulo:
    @pytest.mark.parametrize("texto,esperado", [
        ("REFORMA PEMEX algo mas", "REFORMA PEMEX"),
        ("CERRO DE LA PEZ algo", "CERRO DE LA PEZ"),
        ("reforma pemex en minusculas", "REFORMA PEMEX"),
        ("nada que ver aqui", "ALIMENTOS AL AREA"),
    ])
    def test_detecta_titulo(self, texto, esperado):
        assert titulo_del_pdf(texto) == esperado


class TestObservaciones:
    def test_toma_el_texto_entre_comandas(self):
        texto = (
            "ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0 "
            "MORTERA CON 6 FIRMAS "
            "DEF456 09:00 SHAT CAYO ARCAS 5 GANGWAY 5 0"
        )
        obs = observaciones_por_folio(texto)
        assert "MORTERA" in obs.get("ABC123", "")

    def test_quita_encabezados_del_reporte(self):
        texto = (
            "ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0 "
            "COMANDA DE ALIMENTOS NO. COM. OBSERVACIONES: 10 10 12"
        )
        obs = observaciones_por_folio(texto)
        assert "NO. COM." not in obs.get("ABC123", "")

    def test_quita_la_fecha_del_observado(self):
        texto = (
            "ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0 "
            "MARTES, 13 DE MAYO DE 2026 algo"
        )
        obs = observaciones_por_folio(texto)
        assert "MAYO" not in obs.get("ABC123", "")


class TestComandas:
    def test_campos_basicos(self):
        texto = "ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0"
        comandas = comandas_del_texto(texto)
        assert len(comandas) == 1
        c = comandas[0]
        assert c.comanda == "ABC123"
        assert c.horario == "08:30"
        assert c.pax == 10
        assert c.menu_1 == 10
        assert c.menu_2 == 0
        assert c.transporte == "GANGWAY"
        assert c.destino.startswith("PAPALOAPAN")
        assert c.tipo == "VIANDA"

    def test_mortera_se_detecta_por_observacion(self):
        texto = (
            "ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0 MORTERA "
            "DEF456 09:00 SHAT CAYO ARCAS 5 GANGWAY 5 0"
        )
        por_folio = {c.comanda: c for c in comandas_del_texto(texto)}
        assert por_folio["ABC123"].tipo == "MORTERA"
        assert por_folio["DEF456"].tipo == "VIANDA"

    def test_folio_repetido_no_duplica(self):
        texto = ("ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0 "
                 "ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0")
        assert len(comandas_del_texto(texto)) == 1

    def test_sin_comandas_devuelve_lista_vacia(self):
        assert comandas_del_texto("texto sin nada que ver") == []

    def test_pax_prioriza_sobre_menu_1(self):
        # El PDF trae la columna de personas y la de menú 1; manda pax.
        texto = "ABC123 08:30 KOL TOV PAPALOAPAN 25 GANGWAY 25 8"
        c = comandas_del_texto(texto)[0]
        assert c.pax == 25
        assert c.menu_1 == 25
        assert c.menu_2 == 8

    @pytest.mark.parametrize("transporte", ["AEREO", "GANGWAY", "MARÍTIMO",
                                            "VIUDA", "CANASTILLA"])
    def test_todos_los_transportes(self, transporte):
        texto = f"ABC123 08:30 KOL TOV PAPALOAPAN 10 {transporte} 10 0"
        c = comandas_del_texto(texto)[0]
        assert c.transporte == transporte

    def test_destino_fuera_de_la_lista_no_se_reconoce(self):
        # Fragilidad real del parser: DESTINO_PATTERN es una lista cerrada.
        # Si el reporte trae un destino nuevo, la comanda NO se ve. Esta
        # documentada para que quede claro que agregar destinos es un cambio
        # consciente, no un accidente.
        texto = "ABC123 08:30 KOL TOV DESTINO QUE NO EXISTE 10 GANGWAY 10 0"
        assert comandas_del_texto(texto) == []

    def test_total_pax(self):
        c = Comanda("A", "08:00", "X", "Y", 10, "GANGWAY", 10, 5, "VIANDA", "")
        assert c.total_pax == 15
