"""
Tests del lector por columnas (`core/comandas/tabla.py`).

La razon de existir del modulo esta en su cabecera. Aqui se fija lo que SI se
puede reconstruir con certeza: los campos que estan EN la linea de la fila
(folio, horario, compania, destino, pax, transporte, menu 1 y menu 2), y el
contrato de `parse_pdf` con el camino de texto plano.

Lo que NO se prueba aqui, a proposito, es la reconstruccion de la columna de
observaciones por geometria: ver "LO QUE ESTE MODULO NO LEE" en `tabla.py`.
"""
import io

import pytest

from core.comandas import tabla
from core.comandas.parser import parse_pdf, texto_del_pdf


# ── Utilidades de columna ───────────────────────────────────────

class TestColumnas:

    def _palabra(self, texto, x0, top=100.0):
        return {"text": texto, "x0": x0, "x1": x0 + 5, "top": top,
                "bottom": top + 8}

    def test_una_palabra_solo_no_entra(self):
        # El destino arranca en 225. Un numero de la columna PAX, que esta en
        # 294, no puede terminar dentro de la banda de DESTINO.
        assert tabla._en_linea([self._palabra("47", 294)], tabla.COL_DESTINO) == ""

    def test_destino_toma_su_banda(self):
        palabras = [self._palabra("ABKATUN-N1", 225),
                    self._palabra("47", 296)]
        assert tabla._en_linea(palabras, tabla.COL_DESTINO) == "ABKATUN-N1"

    def test_destino_con_dos_palabras_se_une_con_espacio(self):
        """`ABKATUN D` son dos palabras en la pagina y un destino solo.

        Sin el espacio quedaria 'ABKATUND', que no aparece en ningun reporte.
        """
        palabras = [self._palabra("ABKATUN", 227), self._palabra("D", 257)]
        assert tabla._unir(palabras) == "ABKATUN D"

    def test_lineas_se_agrupan_por_baseline(self):
        palabras = [
            self._palabra("OCT030", 34, top=114.4),
            self._palabra("05:00", 78, top=114.4),
            # Otra linea, 20 puntos mas abajo.
            self._palabra("OCT027", 34, top=134.4),
        ]
        assert len(tabla._lineas(palabras)) == 2

    def test_palabras_de_una_misma_linea_no_se_parten(self):
        """En el PDF real hay palabras de una misma fila a 0.4 puntos.

        `OCT035` esta en un tamano de fuente y `05:00` en otro, y por eso sus
        baselines no coinciden exactamente. Si se partieran, la fila se perderia.
        """
        palabras = [
            self._palabra("OCT035", 34, top=429.9),
            self._palabra("05:00", 78, top=430.3),
            self._palabra("MICOPERI", 143, top=430.3),
        ]
        assert len(tabla._lineas(palabras)) == 1


# ── Que filas son filas de datos ────────────────────────────────

class TestFilaDeDatos:

    def _linea(self, texto_x):
        return [{"text": t, "x0": x, "x1": x + 5, "top": 114.4,
                 "bottom": 122.4} for t, x in texto_x]

    def test_fila_completa_si(self):
        linea = self._linea([("OCT030", 34), ("05:00", 78), ("SENSIA", 147),
                             ("ABKATUN-N1", 225), ("05", 296), ("AEREO", 339),
                             ("05", 394), ("00", 428)])
        assert tabla._es_fila_de_datos(linea)

    def test_el_encabezado_no_es_fila_de_datos(self):
        """El encabezado trae 'MENU' y '1' pero ningun folio."""
        linea = self._linea([("NO.", 32), ("COM.", 45), ("HORARIO", 73),
                             ("DESTINO", 231), ("No.", 288), ("PAX", 300),
                             ("TRANSPORTE", 330), ("MENU", 385)])
        assert not tabla._es_fila_de_datos(linea)

    def test_el_subtotal_no_es_fila_de_datos(self):
        """El subtotal de bloque son tres numeros, sin folio ni transporte."""
        linea = self._linea([("62", 296), ("62", 394), ("00", 428)])
        assert not tabla._es_fila_de_datos(linea)

    def test_transporte_desconocido_no_es_fila_de_datos(self):
        linea = self._linea([("OCT030", 34), ("05:00", 78), ("ABKATUN-N1", 225),
                             ("05", 296), ("BARCO", 339), ("05", 394),
                             ("00", 428)])
        assert not tabla._es_fila_de_datos(linea)


# ── Errores y degradacion ───────────────────────────────────────

class TestDegradacion:

    def test_basura_no_es_pdf(self):
        with pytest.raises(tabla.ErrorTabla):
            tabla.leer_tabla(b"esto no es un pdf")

    def test_pdf_vacio(self):
        with pytest.raises(tabla.ErrorTabla):
            tabla.leer_tabla(b"")

    def test_parse_pdf_sigue_leyendo_un_pdf_sin_la_tabla(self):
        """Un PDF que no es un concentrado se lee igual, por el camino de texto.

        Es lo que pasa con los machotes de una sola comanda que genera
        `core/comandas/pdf/`: tienen la forma del parser, no la del concentrado.
        Si `parse_pdf` no supiera degradar, dejaria de servir para ellos.
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from comparar_parser import _pdf_de_ejemplo

        r = parse_pdf(_pdf_de_ejemplo())
        assert len(r.comandas) >= 1, "el camino de texto plano dejo de funcionar"

    def test_parse_pdf_sigue_advertiendo_si_no_encuentra_comandas(self):
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica", 10)
        c.drawString(60, 700, "un PDF que no es un reporte de comandas")
        c.save()

        from core.comandas.parser import ErrorProcesandoPDF

        with pytest.raises(ErrorProcesandoPDF):
            parse_pdf(buffer.getvalue())


# ── Conversion a Comanda ───────────────────────────────────────

class TestConversion:

    def _fila(self, **cambios):
        base = dict(folio="OCT047", horario="05:00", compania="TECNO FIRE",
                    destino="ABKATUN-N1", pax=13, transporte="GANGWAY",
                    menu_1=13, menu_2=0)
        base.update(cambios)
        return tabla.Fila(**base)

    def test_menu_1_siempre_vale_pax(self):
        """Regla deliberada: manda el conteo de personas, no la columna de menu.

        El reporte real trae casos donde no coinciden (JUL026: 125 contra 126).
        """
        from core.comandas.parser import _comanda_de_fila

        c = _comanda_de_fila(self._fila(pax=125, menu_1=126), "")
        assert c.pax == 125
        assert c.menu_1 == 125
        assert c.menu_2 == 0

    def test_tipo_mortera_sale_de_la_observacion(self):
        from core.comandas.parser import _comanda_de_fila

        assert _comanda_de_fila(self._fila(), "COMIDA-MORTERA").tipo == "MORTERA"
        assert _comanda_de_fila(self._fila(), "COMIDA-VIANDAS").tipo == "VIANDA"

    def test_las_dos_formas_de_pedir_mortera_cuentan(self):
        """El concentrado del 14-10 las escribe de dos formas distintas."""
        from core.comandas.parser import _comanda_de_fila

        a = _comanda_de_fila(self._fila(), "COMIDA-MORTERA TERMO DE AGUA 20LTS")
        b = _comanda_de_fila(self._fila(), "INCLUIR EN LA MORTERA DE 73PAX")
        assert a.tipo == b.tipo == "MORTERA"


# ── El camino de texto plano no se toco ─────────────────────────

class TestTextPlanoSigueIgual:
    """`comandas_del_texto` no cambio. Si cambia, la tabla esta mintiendo."""

    def test_texto_plano_todavia_lee_una_linea(self):
        from core.comandas.parser import comandas_del_texto

        comandas = comandas_del_texto("ABC123 08:30 KOL TOV PAPALOAPAN 10 GANGWAY 10 0")
        assert len(comandas) == 1
        assert comandas[0].pax == 10

    def test_destino_fuera_de_la_lista_sigue_sin_leerse(self):
        """La lista cerrada se mantiene para el camino de texto.

        Con columnas el destino ya no hay que adivinarlo, asi que una fila con
        destino desconocido si se lee; pero por texto sigue sin leerse, que es
        como estaba y como esta documentado en DESTINO_PATTERN.
        """
        from core.comandas.parser import comandas_del_texto

        texto = "ABC123 08:30 KOL TOV DESTINO QUE NO EXISTE 10 GANGWAY 10 0"
        assert comandas_del_texto(texto) == []

    def test_el_texto_se_sigue_generando_igual(self):
        """`texto_del_pdf` no cambio: cada comanda queda en una sola linea.

        El aplanado solo junta el salto que precede a un folio (`\\n(?![A-Z]{3}
        \\d+\\s)`), que es justo lo que evita que un regex de comanda se corte a
        la mitad. Los demas saltos se conservan.
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        from comparar_parser import _pdf_de_ejemplo

        texto = texto_del_pdf(_pdf_de_ejemplo())
        for linea in texto.split("\n"):
            if linea.strip().startswith("ABC123"):
                assert "08:30" in linea, "el folio quedo partido de su horario"
                assert "GANGWAY" in linea
        assert "ABC123 08:30 KOL TOV PAPA LOAPAN 10 GANGWAY 10 0" in texto