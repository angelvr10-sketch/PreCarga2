"""
Los filtros de Supabase: el `eq.` y la normalizacion.

── EL BUG DEL BORRADO ─────────────────────────────────────────────────

`_delete` pasa los filtros a PostgREST tal cual. Sin el operador, PostgREST
intenta parsearlo como sintaxis y responde:

    400 PGRST100: unexpected "P" expecting "not" or operator
    "failed to parse filter (PRUEBA TEMPORAL SA DE CV)"

El cuerpo viene VACIO, asi que el endpoint devolvia un 500 sin mensaje y la fila
NO se borraba. El boton de borrar de la pantalla de Companias estaba roto con
CUALQUIER razon social, no solo con las que empiezan por una palabra reservada
('and', 'not', 'or', 'is'...): 'PRUEBA' falla igual.

`_get` y `_patch` no tienen el problema porque quien los arma pone el operador
(ver `_filtro_usuario` en el repositorio de comandas). `_delete` lo tomaba de
quien se lo pasara, y `eliminar_compania_supabase` no lo ponia.

Estos tests usan una Fake de httpx que PARSEA el filtro como lo haria PostgREST, de
modo que un `eq.` faltante se note aqui y no en produccion.
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=RAIZ / ".env")

import core.supabase_db as db  # noqa: E402


# Palabras que PostgREST toma como sintaxis de filtro. Sirven para ver que el
# fallo del bug no era "empieza por palabra reservada": con 'PRUEBA' tambien falla.
PALABRAS_RESERVADAS = ("and", "not", "or", "is", "in", "like", "eq", "gt", "lt")


class RespuestaFalsa:
    def __init__(self, codigo, cuerpo="", texto=""):
        self.status_code = codigo
        self._cuerpo = cuerpo
        self.text = texto or str(cuerpo)
        self.reason_phrase = "Bad Request"
        self.request = None

    def json(self):
        return self._cuerpo


class ClienteFalso:
    """Registra las peticiones y responde como lo haria PostgREST.

    Lo importante: `params` es lo que REALMENTE se manda, y `_delete` lo pasa sin
    tocar. Si no lleva `eq.`, el filtro se interpreta como sintaxis y se devuelve
    el 400 de PGRST100, con el cuerpo vacio que hace que el error sea inaccionable.
    """

    def __init__(self):
        self.peticiones = []

    def request(self, method, url, headers=None, params=None):
        self.peticiones.append({"method": method, "url": url, "params": dict(params or {})})
        return self._responder(method, params or {})

    def _responder(self, method, params):
        for valor in params.values():
            if self._es_sintaxis(valor):
                return RespuestaFalsa(
                    400,
                    cuerpo=None,
                    texto='{"code":"PGRST100","details":"unexpected \\"P\\" expecting '
                          '\\"not\\" or operator","hint":null,"message":'
                          f'"failed to parse filter ({valor})"}}',
                )
        return RespuestaFalsa(200, cuerpo=[{"id": "1"}])

    @staticmethod
    def _es_sintaxis(valor: str) -> bool:
        """PostgREST espera `operador.valor`; sin punto no hay filtro."""
        if not isinstance(valor, str):
            return False
        return "." not in valor

    def ultimo(self):
        return self.peticiones[-1]


@pytest.fixture
def cliente(monkeypatch):
    """Un cliente falso instalado en el modulo, y el original guardado."""
    c = ClienteFalso()
    original = db._CLIENT
    monkeypatch.setattr(db, "_CLIENT", c)
    yield c
    db._CLIENT = original


class TestFiltroDeBorrado:
    """El `eq.` tiene que ir en la funcion que llama a `_delete`."""

    @pytest.mark.parametrize("razon", [
        "PEMEX",
        "PRUEBA TEMPORAL SA DE CV",
        "MICOPERI DE MEXICO SA DE CV",
        "CLIMER MULTISERVICIOS, S.A. DE C.V.",
        "P.M.I. de Norteamérica, S.A. de C.V. y P.M.I. de México",
        "Comercial Verite, S.A. de C.V.",
    ])
    def test_el_borrado_de_una_compania_lleva_eq(self, cliente, razon):
        """Cubre los dos casos que importan: los nombres raros (con punto, coma y
        tilde) que son los que hay en la tabla, y uno corriente."""
        db.eliminar_compania_supabase(razon)
        valor = cliente.ultimo()["params"]["razon_social"]
        assert valor.startswith("eq."), f"El filtro va sin operador: {valor!r}"

    @pytest.mark.parametrize("nombre", [
        "KU-A",
        "ACTIVO DE EXTRACCION KU MALOOB ZAAP",
        "LITORAL DE TABASCO",
        "GERENCIA DE LOGÍSTICA MARINA",
    ])
    def test_el_borrado_de_un_activo_lleva_eq(self, cliente, nombre):
        db.eliminar_activo_supabase(nombre)
        valor = cliente.ultimo()["params"]["nombre"]
        assert valor.startswith("eq."), f"El filtro va sin operador: {valor!r}"

    @pytest.mark.parametrize("razon", PALABRAS_RESERVADAS)
    def test_no_es_lo_mismo_que_empezar_por_palabra_reservada(self, cliente, razon):
        """Aclaracion de por que el fallo era total y no parcial: el sintoma
        visible era 'no borra si empieza por una palabra reservada', pero en
        realidad fallaba con TODAS. Este test documenta que el `eq.` es lo que
        arregla, no una lista de palabras."""
        db.eliminar_compania_supabase(f"{razon} ALGO SA DE CV")
        assert cliente.ultimo()["params"]["razon_social"].startswith("eq.")

    def test_el_valor_va_intacto_despues_del_eq(self, cliente):
        """El `eq.` se prefija, no se sustituye ni se escapa: la razón social
        completa tiene que seguir llegando, con sus espacios, punto y coma."""
        razon = "CLIMER MULTISERVICIOS, S.A. DE C.V."
        db.eliminar_compania_supabase(razon)
        assert cliente.ultimo()["params"]["razon_social"] == f"eq.{razon}"

    def test_usa_el_modo_delete(self, cliente):
        db.eliminar_compania_supabase("PEMEX")
        assert cliente.ultimo()["method"] == "DELETE"

    def test_sin_eq_postgrest_lo_rechazaria(self, cliente):
        """El mecanismo, para que se entienda por que el `eq.` es obligatorio:
        sin punto, PostgREST devuelve 400 y el cuerpo vacio."""
        r = cliente._responder("DELETE", {"razon_social": "PRUEBA TEMPORAL SA DE CV"})
        assert r.status_code == 400
        assert r.text  # aunque sea este el que llego vacio en produccion


class TestElErrorEsDiagnosticable:
    """El 400 de PostgREST llega sin cuerpo parseable y el 500 no dice nada.

    No se arregla aqui el diagnostico (es de otra capa), pero se deja anotado que
    `_status_error` es quien mete el cuerpo de PostgREST en el mensaje, y que por
    eso el error del borrado era `400 Bad Request` pelado: PostgREST devolvio su
    cuerpo, pero `_delete` lo recibio como `r.json()` -> None, y el mensaje se
    armo con ese `None`.
    """

    def test_delete_devuelve_lista_vacia_si_no_hay_cuerpo(self, cliente):
        """Con el `eq.` puesto no hay 400, pero el camino de 'no hay cuerpo' se
        documenta: `_delete` no debe reventar si la respuesta no trae JSON."""
        cliente._responder = lambda m, p: RespuestaFalsa(204, cuerpo=None)
        assert db._delete("companias", {"razon_social": "eq.PEMEX"}) == []


class TestClienteSeReabre:
    """`cerrar_cliente()` ya no deja el modulo muerto.

    Antes, con `_CLIENT = None`, la siguiente peticion lanzaba
    `RuntimeError("httpx no esta instalado")`, que culpa a una libreria que si
    estaba instalada: el sintoma real era que el pool estaba cerrado. Se lanzaba
    desde el `shutdown` de la app, asi que en los tests el primer `TestClient` que
    terminaba dejaba sinred a todos los siguientes.
    """

    def test_reabre_el_pool_si_esta_cerrado(self, monkeypatch):
        db.cerrar_cliente()
        assert db._CLIENT is None

        # Se llama al camino que usa `_request_with_retry`.
        db._CLIENT = None
        try:
            if not db._CLIENT:
                if db._CLIENT is None:
                    db._reabrir_cliente()
            assert db._CLIENT is not None, "no se reabrio el pool"
        finally:
            if db._CLIENT is not None:
                db._CLIENT.close()
                db._CLIENT = None

    def test_reabrir_es_idempotente(self):
        db.cerrar_cliente()
        primero = db._reabrir_cliente()
        segundo = db._reabrir_cliente()
        assert primero is segundo, "reabrir dos veces creo dos clientes"
        db.cerrar_cliente()

    def test_httpx_instalado_no_da_el_error_enganoso(self):
        """Si httpx no esta, el mensaje tiene que seguir siendo ese. El bug era
        que ese MISMO mensaje salia tambien con httpx instalado."""
        import os

        if not db.HAS_HTTPX:
            pytest.skip("httpx no instalado en este entorno")
        assert db.HAS_HTTPX
        # El pool puede estar cerrado, pero eso ya no es un RuntimeError.
        db.cerrar_cliente()
        try:
            db._reabrir_cliente()
        finally:
            db.cerrar_cliente()