"""Fechas en espanol. Cubren el bug de locale que traia la app de Streamlit."""
from datetime import date

import pytest

from core.comandas.fecha import (
    DIAS_ES,
    fecha_corta_es,
    fecha_largo_es,
    fecha_titulo_es,
    hoy,
    iso_desde_texto_pdf,
    resolver_fecha_operacion,
    texto_fecha_del_pdf,
)


class TestFormato:
    def test_fecha_larga_con_dia_de_semana(self):
        # 13/05/2026 es un miércoles, CON acento: es lo que imprime la app
        # original (app.py:358) y lo que trae el golden de salida.
        assert fecha_largo_es(date(2026, 5, 13)) == "MIÉRCOLES, 13 DE MAYO DE 2026"

    def test_dias_con_acento_se_conservan(self):
        """MIÉRCOLES y SÁBADO se escriben con acento, también en el machote.

        Una versión anterior del módulo normalizaba a 'MIERCOLES' y 'SABADO'.
        El golden de salida (Tests las_las_Comandas_REFORMA_PEMEX.pdf,
        página 1) demuestra que el original imprime 'MIÉRCOLES', y eso es lo que
        se firma en el muelle.
        """
        assert fecha_largo_es(date(2026, 10, 7)).startswith("MIÉRCOLES")
        assert fecha_largo_es(date(2026, 10, 10)).startswith("SÁBADO")
        assert "MIERCOLES" not in fecha_largo_es(date(2026, 10, 7))
        assert "SABADO" not in fecha_largo_es(date(2026, 10, 10))

    def test_indice_de_dias_alineado_con_weekday(self):
        # El bug clásico: Monday=0 en Python, domingo=0 en el calendario
        # impreso. Si el array esta corrido, todas las fechas salen con el día
        # equivocado.
        for dia in range(1, 8):
            f = date(2026, 5, dia)
            assert DIAS_ES[f.weekday()] in fecha_largo_es(f)
        assert fecha_largo_es(date(2026, 5, 11)).startswith("LUNES")    # lunes
        assert fecha_largo_es(date(2026, 5, 17)).startswith("DOMINGO")  # domingo

    def test_titulo_para_pantalla_lleva_acentos(self):
        assert fecha_titulo_es(date(2026, 5, 13)) == "miércoles, 13 de mayo de 2026"

    def test_corta_con_ceros_a_la_izquierda(self):
        assert fecha_corta_es(date(2026, 5, 3)) == "03/05/2026"


class TestDesdeTexto:
    def test_extrae_de_encabezado(self):
        assert texto_fecha_del_pdf(
            "CONTROL DE ENTREGA ALIMENTOS AL AREA DEL DIA: LUNES, 1 DE JUNIO DE 2026"
        ) == "LUNES, 1 DE JUNIO DE 2026"

    def test_conserva_el_acento_del_dia(self):
        # El pie del reporte real viene en minúsculas y con acentos:
        # 'miércoles, 13 de mayo de 2026'. Se lee tal cual, en mayúsculas.
        assert texto_fecha_del_pdf("miércoles, 13 de mayo de 2026") == "MIÉRCOLES, 13 DE MAYO DE 2026"

    def test_texto_sin_fecha_devuelve_none(self):
        assert texto_fecha_del_pdf("no hay fecha aqui") is None

    def test_iso_con_dia_de_semana(self):
        assert iso_desde_texto_pdf("MARTES, 13 DE MAYO DE 2026") == "2026-05-13"

    def test_iso_sin_dia_de_semana(self):
        assert iso_desde_texto_pdf("13 DE MAYO DE 2026") == "2026-05-13"

    def test_iso_completa_el_dia_a_dos_digitos(self):
        assert iso_desde_texto_pdf("VIERNES, 3 DE ENERO DE 2025") == "2025-01-03"

    def test_iso_mes_desconocido_devuelve_none(self):
        # No debe reventar ni inventar un mes.
        assert iso_desde_texto_pdf("LUNES, 13 DE QUINTUBRE DE 2026") is None

    def test_iso_texto_vacio(self):
        assert iso_desde_texto_pdf("") is None


class TestPrioridadDeFecha:
    def test_gana_la_del_pdf(self):
        iso, texto = resolver_fecha_operacion("LUNES, 1 DE JUNIO DE 2026")
        assert iso == "2026-06-01"
        assert texto == "LUNES, 1 DE JUNIO DE 2026"

    def test_sin_fecha_en_el_pdf_usa_hoy(self):
        iso, texto = resolver_fecha_operacion("reporte sin fecha")
        assert iso == hoy().isoformat()
        # Los dias CON y SIN tilde. Esta asercion vivia con la lista sin acentos
        # ("MIERCOLES", "SABADO"), asi que pasaba 5 dias de la semana y fallaba
        # los dos con tilde: un test que solo se ejecuta de verdad el 71% de las
        # veces. El que hoy (2026-10-07) es MIÉRCOLES, y aqui lo atrapa.
        #
        # El codigo NO se cambia para esto: el machote exige MIÉRCOLES y SÁBADO CON
        # acento (ver test de arriba y app.py:358).
        assert texto.startswith(("LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES",
                                  "VIERNES", "SÁBADO", "SABADO", "DOMINGO"))

    def test_mes_ilegible_no_revienta(self):
        # Fecha con texto pero no parseable: usa hoy, sin excepcion.
        iso, texto = resolver_fecha_operacion("LUNES, 13 DE QUINTUBRE DE 2026")
        assert iso == hoy().isoformat()
        assert "DE" in texto
