"""
Tests de `core.comandas.edicion` — la validacion de una comanda capturada a mano.

Es una funcion pura: estos tests no levantan el servidor, no tocan Supabase y no
generan PDF. Comprueban las dos cosas que pueden salir mal cuando el cuerpo de
la peticion lo escribe el navegador:

  1. que un dato invalido NO llegue a la base (se rechaza con un mensaje que
     dice que campo y por que);
  2. que los datos que SI llegan queden normalizados (folio en mayusculas,
     horario a HH:MM, MARITIMO -> MARÍTIMO), para que dos capturas del mismo
     dato no se guarden con dos formas distintas.
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from core.comandas import edicion  # noqa: E402
from core.comandas.edicion import (  # noqa: E402
    ErrorComandaInvalida,
    comanda_desde_payload,
)


def _payload(**kwargs):
    """Un cuerpo valido al que se le cambia solo lo que prueba cada test."""
    datos = {
        "comanda": "OCT001",
        "horario": "06:30",
        "compania": "NORCONTROL",
        "destino": "ABKATUN A",
        "pax": 10,
        "transporte": "GANGWAY",
        "tipo": "VIANDA",
        "observaciones": "COMIDA-VIANDA",
    }
    datos.update(kwargs)
    return datos


# ── Folio ──────────────────────────────────────────────────────

class TestFolio:

    def test_se_pasa_a_mayusculas(self):
        assert edicion.normalizar_folio("oct001") == "OCT001"

    def test_quita_espacios_interiores(self):
        """Un folio con espacio rompe la URL del PDF individual."""
        assert edicion.normalizar_folio(" oct 001 ") == "OCT001"

    @pytest.mark.parametrize("valor", ["", "   ", None])
    def test_vacio_es_error(self, valor):
        with pytest.raises(ErrorComandaInvalida) as exc:
            edicion.normalizar_folio(valor)
        assert exc.value.campo == "folio"

    @pytest.mark.parametrize("valor", ["OCT@001", "OCT#1", "ÑANDU1", "%20"])
    def test_caracteres_raros_son_error(self, valor):
        with pytest.raises(ErrorComandaInvalida):
            edicion.normalizar_folio(valor)

    def test_admite_guion_barra_y_punto(self):
        """Hay folios historicos con esos separadores."""
        for folio in ("PB-LIT", "CIA/CG", "OCH.TAN", "T-SIMIN1"):
            assert edicion.normalizar_folio(folio) == folio

    def test_demasiado_largo_es_error(self):
        with pytest.raises(ErrorComandaInvalida):
            edicion.normalizar_folio("X" * 25)

    def test_folio_existente_no_se_normaliza(self):
        """Al modificar, la llave se usa tal cual: hay filas viejas en
        minusculas y buscar en mayusculas daria un 404 sobre una fila visible."""
        assert edicion.folio_existente("oct001") == "oct001"
        assert edicion.folio_existente(" OCT001 ") == "OCT001"


# ── Horario ────────────────────────────────────────────────────

class TestHorario:

    def test_normaliza_a_dos_cifras(self):
        assert edicion.normalizar_horario("6:5") == "06:05"
        assert edicion.normalizar_horario("18:30") == "18:30"

    def test_quita_espacios(self):
        assert edicion.normalizar_horario("  07:05  ") == "07:05"

    @pytest.mark.parametrize("valor", ["", None, "6", "06-30", "6:5:1", "24:00",
                                       "12:60", "abc"])
    def test_invalido_es_error(self, valor):
        with pytest.raises(ErrorComandaInvalida) as exc:
            edicion.normalizar_horario(valor)
        assert exc.value.campo == "horario"


# ── Tipo y transporte ──────────────────────────────────────────

class TestTipo:

    def test_por_defecto_vianda(self):
        assert edicion.normalizar_tipo(None) == "VIANDA"
        assert edicion.normalizar_tipo("") == "VIANDA"

    def test_acepta_minusculas(self):
        assert edicion.normalizar_tipo("mortera") == "MORTERA"

    def test_cualquier_otra_cosa_es_error(self):
        with pytest.raises(ErrorComandaInvalida) as exc:
            edicion.normalizar_tipo("MORTERAS")
        assert "MORTERA o VIANDA" in str(exc.value)


class TestTransporte:

    def test_normaliza_mayusculas(self):
        assert edicion.normalizar_transporte("gangway") == "GANGWAY"

    def test_acepta_maritimo_sin_acento(self):
        """El PDF imprime MARÍTIMO; la gente teclea MARITIMO."""
        assert edicion.normalizar_transporte("MARITIMO") == "MARÍTIMO"

    def test_vacio_se_admite(self):
        """Hay comandas que se capturan antes de saber el transporte."""
        assert edicion.normalizar_transporte(None) == ""
        assert edicion.normalizar_transporte("  ") == ""

    def test_fuera_de_la_lista_es_error(self):
        with pytest.raises(ErrorComandaInvalida) as exc:
            edicion.normalizar_transporte("CAMION")
        assert exc.value.campo == "transporte"


# ── Numeros ────────────────────────────────────────────────────

class TestNumeros:

    def test_acepta_texto(self):
        """Un <input> manda '12', no 12."""
        c = comanda_desde_payload(_payload(pax="12"))
        assert c.pax == 12

    def test_menu_1_se_copia_de_pax(self):
        """Es el invariante del parser: en el reporte, MENU 1 son las mismas
        personas que PAX."""
        c = comanda_desde_payload(_payload(pax=7))
        assert (c.pax, c.menu_1, c.menu_2) == (7, 7, 0)

    def test_pax_es_la_suma_de_los_menus(self):
        """PAX no se captura: es Menu 1 + Menu 2, aunque el cuerpo diga otra cosa."""
        c = comanda_desde_payload(_payload(pax=125, menu_1=126, menu_2=3))
        assert (c.pax, c.menu_1, c.menu_2) == (129, 126, 3)

    def test_pax_recibido_incoherente_se_ignora(self):
        c = comanda_desde_payload(_payload(pax=99, menu_1=10, menu_2=2))
        assert c.pax == 12

    def test_menu_2_suma_aparte(self):
        c = comanda_desde_payload(_payload(pax=10, menu_2="4"))
        assert c.total_pax == 14

    def test_sin_personas_es_error(self):
        with pytest.raises(ErrorComandaInvalida) as exc:
            comanda_desde_payload(_payload(pax=0, menu_1=0, menu_2=0))
        assert exc.value.campo == "pax"

    def test_la_suma_tambien_tiene_tope(self):
        """Dos menus validos por separado no pueden sumar una fila absurda."""
        with pytest.raises(ErrorComandaInvalida) as exc:
            comanda_desde_payload(_payload(pax=10, menu_1=6000, menu_2=6000))
        assert exc.value.campo == "pax"

    @pytest.mark.parametrize("valor", [-1, "muchos", 10.5, True, 100_000])
    def test_valores_absurdos_son_error(self, valor):
        with pytest.raises(ErrorComandaInvalida):
            comanda_desde_payload(_payload(pax=valor))


# ── Textos ─────────────────────────────────────────────────────

class TestTextos:

    def test_colapsa_espacios(self):
        c = comanda_desde_payload(_payload(compania="  NOR   CONTROL ",
                                           destino="ABKATUN   A"))
        assert c.compania == "NOR CONTROL"
        assert c.destino == "ABKATUN A"

    @pytest.mark.parametrize("campo", ["compania", "destino"])
    def test_son_obligatorios(self, campo):
        with pytest.raises(ErrorComandaInvalida) as exc:
            comanda_desde_payload(_payload(**{campo: "   "}))
        assert exc.value.campo == campo

    def test_observaciones_largas_son_error(self):
        with pytest.raises(ErrorComandaInvalida):
            comanda_desde_payload(_payload(observaciones="x" * 501))

    def test_observaciones_vacias_se_admiten(self):
        assert comanda_desde_payload(_payload(observaciones=None)).observaciones == ""


# ── Punto de entrada ───────────────────────────────────────────

class TestComandaDesdePayload:

    def test_devuelve_una_comanda_completa(self):
        c = comanda_desde_payload(_payload())
        assert c.a_dict() == {
            "comanda": "OCT001", "horario": "06:30", "compania": "NORCONTROL",
            "destino": "ABKATUN A", "pax": 10, "transporte": "GANGWAY",
            "menu_1": 10, "menu_2": 0, "tipo": "VIANDA",
            "observaciones": "COMIDA-VIANDA",
        }

    def test_el_cuerpo_tiene_que_ser_un_objeto(self):
        with pytest.raises(ErrorComandaInvalida):
            comanda_desde_payload(["no", "es", "un", "objeto"])

    def test_al_modificar_el_folio_manda_la_url(self):
        c = comanda_desde_payload(_payload(comanda=None), folio="OCT001")
        assert c.comanda == "OCT001"

    def test_al_modificar_el_folio_conserva_la_caja_de_la_base(self):
        """Una fila historica guardada como 'oct001' se tiene que poder editar
        sin que el UPDATE busque 'OCT001' y no encuentre nada."""
        c = comanda_desde_payload(_payload(comanda=None), folio="oct001")
        assert c.comanda == "oct001"

    def test_al_modificar_no_se_puede_cambiar_el_folio(self):
        with pytest.raises(ErrorComandaInvalida) as exc:
            comanda_desde_payload(_payload(comanda="OTRO1"), folio="OCT001")
        assert "no se puede cambiar" in str(exc.value)
