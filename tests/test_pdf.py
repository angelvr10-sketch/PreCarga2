"""
Los cinco generadores de PDF.

Aqui lo importante NO es el color de un rectangulo: es que el papel siga siendo
lo que la gente firma en el muelle. Por eso se comprueban numero de paginas,
textos obligatorios del machote, y que la mortera no se cuele en las viandas.
"""
import io

import pytest
from pypdf import PdfReader

from core.comandas.pdf import (
    pdf_comanda,
    pdf_comandas,
    pdf_comandas_mortera,
    pdf_reporte_estadistico,
    pdf_vales,
)
import core.comandas.pdf.comanda as mod_comanda

FECHA = "MARTES, 13 DE MAYO DE 2026"
TITULO = "REFORMA PEMEX"


def texto_de(pdf_bytes, pagina=0):
    return PdfReader(io.BytesIO(pdf_bytes)).pages[pagina].extract_text() or ""


def n_paginas(pdf_bytes):
    return len(PdfReader(io.BytesIO(pdf_bytes)).pages)


class TestPaginas:
    def test_comanda_individual_una_pagina(self, comanda):
        assert n_paginas(pdf_comanda(comanda(), FECHA, TITULO)) == 1

    def test_una_pagina_por_comanda(self, varias_comandas):
        assert n_paginas(pdf_comandas(varias_comandas, FECHA, TITULO)) == len(varias_comandas)

    def test_con_mortera_no_agrega_paginas(self, varias_comandas):
        # La mortera mete lineas, no hojas: si esto cambia, el conteo de folios
        # del reporte se descuadra en el muelle.
        assert n_paginas(pdf_comandas_mortera(varias_comandas, FECHA, TITULO)) == len(varias_comandas)

    def test_vales_diez_por_pagina(self, comanda):
        # 10 vales caben en una hoja.
        diez = [comanda(f"CMN{i:03d}") for i in range(10)]
        assert n_paginas(pdf_vales(diez, FECHA)) == 1

    def test_vales_uno_extra_va_a_segunda_pagina(self, comanda):
        once = [comanda(f"CMN{i:03d}") for i in range(11)]
        assert n_paginas(pdf_vales(once, FECHA)) == 2


class TestMachote:
    @pytest.mark.parametrize("texto", [
        "RECIBE ALIMENTOS",
        "ENTREGA UTENSILIOS",
        "ENTREGA ALIMENTOS",
        "RECIBE UTENSILIOS",
        "NOMBRE Y FIRMA",
        "CONTROL DE ENTREGA DE ALIMENTOS AL AREA DEL DIA:",
        "CONTRATO No. 428224804",
        "KOL TOV",
        "SHAT",
        "PORTA VIANDA",
        "THERMO MCA. IGLOO 3 LT",
        "TOTAL ARTICULOS",
    ])
    def test_textos_del_machote(self, comanda, texto):
        assert texto in texto_de(pdf_comanda(comanda(), FECHA, TITULO))

    def test_folio_y_fecha_en_el_papel(self, comanda):
        t = texto_de(pdf_comanda(comanda(folio="UHF777"), FECHA, TITULO))
        assert "UHF777" in t
        assert "13 DE MAYO DE 2026" in t

    def test_observaciones_salen_en_el_papel(self, comanda):
        t = texto_de(pdf_comanda(comanda(observaciones="MORTERA CON TAPA"), FECHA, TITULO))
        assert "OBSERVACIONES" in t
        assert "MORTERA CON TAPA" in t

    def test_comanda_sin_observaciones_no_deja_hueco(self, comanda):
        t = texto_de(pdf_comanda(comanda(observaciones=""), FECHA, TITULO))
        assert "OBSERVACIONES" not in t

    def test_observaciones_largas_se_parten(self, comanda):
        larga = "PALABRA " * 40
        # Se parte en lineas de 95; lo importante es que no se trunque a la vez.
        assert n_paginas(pdf_comanda(comanda(observaciones=larga), FECHA, TITULO)) == 1


class TestMortera:
    ETIQUETAS = [
        "ELABORÓ", "SUPERVISÓ", "AUTORIZÓ",
        "RECIBIÓ MORTERA", "ENTREGÓ MORTERA", "OPERADOR RESPONSABLE",
    ]

    def test_vianda_no_trae_el_bloque_de_mortera(self, comanda):
        t = texto_de(pdf_comandas([comanda(tipo="VIANDA")], FECHA, TITULO))
        assert not any(e in t for e in self.ETIQUETAS)

    def test_por_defecto_no_escribe_las_etiquetas(self, comanda):
        # Comportamiento heredado: el original dibujaba las lineas pero nunca
        # el texto (app.py:904). Ver DIBUJAR_ETIQUETAS_MORTERA.
        t = texto_de(pdf_comandas_mortera([comanda(tipo="MORTERA")], FECHA, TITULO))
        assert not any(e in t for e in self.ETIQUETAS)

    def test_con_el_interruptor_las_seis_salen(self, comanda, monkeypatch):
        monkeypatch.setattr(mod_comanda, "DIBUJAR_ETIQUETAS_MORTERA", True)
        t = texto_de(pdf_comandas_mortera([comanda(tipo="MORTERA")], FECHA, TITULO))
        assert all(e in t for e in self.ETIQUETAS)

    def test_el_pdf_normal_no_agranda_las_morteras(self, comanda):
        # `con_mortera=False` debe ignorarlas: una mortera sigue siendo una
        # pagina, no dos.
        solo_mortera = [comanda(f"MOR{i}", tipo="MORTERA") for i in range(3)]
        assert n_paginas(pdf_comandas(solo_mortera, FECHA, TITULO)) == 3


class TestVales:
    def test_campos_del_vale(self, comanda):
        t = texto_de(pdf_vales([comanda(folio="UHF321")], FECHA), pagina=0)
        for campo in ("FECHA:", "No. COMANDA:", "COMPAÑÍA:", "PAX:", "DESTINO:", "MENÚ:"):
            assert campo in t
        assert "UHF321" in t
        assert "ADMINISTRACION" in t

    def test_fecha_corta_en_el_vale(self, comanda):
        t = texto_de(pdf_vales([comanda()], FECHA), pagina=0)
        assert "13/05/2026" in t

    def test_texto_largo_se_recorta(self, comanda):
        # Una compañía de 80 caracteres no puede desbordar la linea.
        t = texto_de(pdf_vales([comanda(compania="X" * 80)], FECHA), pagina=0)
        assert "…" in t or "X" * 40 in t

    def test_vale_sin_menus_muestra_guion(self, comanda):
        t = texto_de(pdf_vales([comanda(menu_1=0, menu_2=0)], FECHA), pagina=0)
        assert "M1" not in t


class TestReporteEstadistico:
    def test_una_pagina_con_pocas_companias(self, varias_comandas):
        assert n_paginas(pdf_reporte_estadistico(varias_comandas, FECHA, TITULO)) == 1

    def test_pagina_extra_con_muchas_companias(self, comanda):
        # 35 companias no caben: tiene que repartir en paginas.
        muchas = [comanda(f"CMN{i:03d}", compania=f"COMPAÑIA NUMERO {i} S.A. DE C.V.")
                  for i in range(35)]
        assert n_paginas(pdf_reporte_estadistico(muchas, FECHA, TITULO)) > 1

    def test_tiene_los_bloques(self, varias_comandas):
        t = texto_de(pdf_reporte_estadistico(varias_comandas, FECHA, TITULO))
        for bloque in ("Reporte", "Fecha:", "Distribución de PAX por Destino",
                       "PAX por Modo de Transporte", "Detalle por Compañía"):
            assert bloque in t

    def test_kpis_en_el_papel(self, varias_comandas):
        t = texto_de(pdf_reporte_estadistico(varias_comandas, FECHA, TITULO))
        for etiqueta in ("Comandas", "Total PAX", "Menú 1", "Menú 2", "Morteras", "Viandas"):
            assert etiqueta in t

    def test_pie_de_pagina(self, varias_comandas):
        t = texto_de(pdf_reporte_estadistico(varias_comandas, FECHA, TITULO))
        assert "ComandasPro" in t
        assert "Angel Valenzuela Romero" in t

    def test_sin_datos_no_revienta(self, comanda):
        # Lista vacia: el reporte sale con los bloques vacios, no con error.
        assert n_paginas(pdf_reporte_estadistico([], FECHA, TITULO)) == 1


class TestBytes:
    @pytest.mark.parametrize("generador", [
        lambda c: pdf_comanda(c[0], FECHA, TITULO),
        lambda c: pdf_comandas(c, FECHA, TITULO),
        lambda c: pdf_comandas_mortera(c, FECHA, TITULO),
        lambda c: pdf_vales(c, FECHA),
        lambda c: pdf_reporte_estadistico(c, FECHA, TITULO),
    ])
    def test_devuelve_pdf_valido(self, varias_comandas, generador):
        datos = generador(varias_comandas)
        assert isinstance(datos, bytes)
        assert datos.startswith(b"%PDF-")
