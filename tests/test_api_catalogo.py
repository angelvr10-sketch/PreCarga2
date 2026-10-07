"""
Los seis endpoints de companias y activos.

Lo que cubren:

  1. AUTENTICACION. Antes ninguno exigia sesion: con la URL a mano, cualquiera
     podia POSTear o DELETEear. Eso permitia, por ejemplo, borrar la razon social
     que el procesador usa para el alias de la celda E8, y el Excel salia con el
     nombre largo sin que nadie supiera por que.

  2. DUPLICADOS. `_post` inserta sin comprobar nada, asi que dos Guardar
     seguidos dejaban dos filas con la misma razon social. Con la fila repetida,
     `obtener_nombre_compania` devuelve la PRIMERA que encuentra, que no
     necesariamente es la que el usuario acaba de escribir.

  3. LA CACHE. Cada alta o baja tiene que invalidar el catalogo de
     `core/catalogo.py`. Sin eso, lo agregado desde la UI tardaba hasta 5
     minutos en verse en los Excel, que es justo lo que reporto el usuario al
     empezar ("la compania esta en la tabla pero el alias no sale").

No tocan Supabase: se falsean las tres funciones de `core.supabase_db` que usa
este router y `get_user_from_token` para la sesion.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=RAIZ / ".env")

import main  # noqa: E402

ADMIN = {"id": "1", "username": "admin", "rol": "admin"}


class CatalogoFalso:
    """Tablas `companias` y `activos` en memoria, con la misma forma que Supabase."""

    def __init__(self):
        self.companias = [
            {"razon_social": "MICOPERI DE MEXICO SA DE CV", "nombre_corto": "MICOPERI"},
            {"razon_social": "PEMEX", "nombre_corto": "PEMEX"},
        ]
        # `leer_activos_supabase` devuelve STRINGS, no filas. Es su firma real y
        # el catalogo la respeta.
        self.activos = ["KU-A", "PLATAFORMA CAMPECHE"]

    def leer_companias(self):
        return [dict(c) for c in self.companias]

    def agregar_compania(self, razon_social, nombre_corto):
        self.companias.append(
            {"razon_social": razon_social, "nombre_corto": nombre_corto}
        )
        return {"id": str(len(self.companias))}

    def eliminar_compania(self, razon_social):
        # Reproduce el `eq.` que ahora pone `eliminar_compania_supabase`. El doble
        # tiene que respetarlo o el test pasaria sin comprobar nada: si se acepta
        # la razon social cruda, aqui se compararia contra 'eq.PEMEX' y no borraria
        # nada, dando verde con la fila intacta.
        if razon_social.startswith("eq."):
            razon_social = razon_social[3:]
        antes = len(self.companias)
        self.companias = [
            c for c in self.companias
            if c["razon_social"] != razon_social
        ]
        return antes != len(self.companias)

    def leer_activos(self):
        return list(self.activos)

    def agregar_activo(self, nombre):
        self.activos.append(nombre)
        return {"id": str(len(self.activos))}

    def eliminar_activo(self, nombre):
        if nombre.startswith("eq."):
            nombre = nombre[3:]
        antes = len(self.activos)
        self.activos = [a for a in self.activos if a != nombre]
        return antes != len(self.activos)


@pytest.fixture
def catalogo(monkeypatch):
    """Las tablas en memoria + la cache del catalogo limpia."""
    import core.catalogo as cat
    import routers.api_data as rd

    c = CatalogoFalso()
    monkeypatch.setattr(rd, "leer_companias_supabase", c.leer_companias)
    monkeypatch.setattr(rd, "agregar_compania_supabase", c.agregar_compania)
    monkeypatch.setattr(rd, "eliminar_compania_supabase", c.eliminar_compania)
    monkeypatch.setattr(rd, "leer_activos_supabase", c.leer_activos)
    monkeypatch.setattr(rd, "agregar_activo_supabase", c.agregar_activo)
    monkeypatch.setattr(rd, "eliminar_activo_supabase", c.eliminar_activo)

    # El catalogo de core tambien necesita ver el doble, para poder resolver el
    # alias recien agregado.
    monkeypatch.setattr(cat, "leer_companias_supabase", c.leer_companias)
    monkeypatch.setattr(cat, "leer_activos_supabase", c.leer_activos)

    cat.invalidar_cache()
    yield c
    cat.invalidar_cache()


@pytest.fixture
def cliente():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def sesion(monkeypatch):
    """Pone (o quita) la sesion, sin tocar Supabase."""
    import routers.api_data as rd

    estado = {"usuario": None}

    def _desde_token(token):
        return estado["usuario"] if token else None

    monkeypatch.setattr(rd, "get_user_from_token", _desde_token)
    estado["cookie"] = "test-local"
    return estado


def _entrar(cliente, sesion, usuario=ADMIN):
    sesion["usuario"] = usuario
    cliente.cookies.set("session", sesion["cookie"])


# ── Autenticación ──────────────────────────────────────────────

class TestExigeSesion:

    @pytest.mark.parametrize("metodo,ruta,cuerpo", [
        # GET y DELETE no aceptan `json` en el cliente de pruebas, asi que cada
        # verbo lleva su llamada propia. Antes esta prueba fallaba con
        # "Client.get() got an unexpected keyword argument 'json'", que es un
        # error del TEST y no del endpoint: habria dado verde sin comprobar nada.
        ("get", "/api/companias", None),
        ("delete", "/api/companias/CUALQUIER", None),
        ("get", "/api/activos", None),
        ("delete", "/api/activos/CUALQUIER", None),
        ("post", "/api/companias", {"razon_social": "X SA DE CV", "nombre_corto": "X"}),
        ("post", "/api/activos", {"nombre": "X"}),
    ])
    def test_sin_sesion_es_401(self, cliente, catalogo, sesion, metodo, ruta, cuerpo):
        """El hallazgo: los seis endpoints aceptaban peticiones sin cookie."""
        sesion["usuario"] = None
        cliente.cookies.clear()
        if metodo == "get":
            r = cliente.get(ruta)
        elif metodo == "delete":
            r = cliente.delete(ruta)
        else:
            r = cliente.post(ruta, json=cuerpo)
        assert r.status_code == 401, f"{metodo.upper()} {ruta} devolvio {r.status_code}"

    def test_con_sesion_normal_si_pasa(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        assert cliente.get("/api/companias").status_code == 200

    def test_el_401_impide_agregar_de_verdad(self, cliente, catalogo, sesion):
        """No basta con el status: la fila no debe haberse creado."""
        sesion["usuario"] = None
        cliente.cookies.clear()
        antes = len(catalogo.companias)
        cliente.post(
            "/api/companias",
            json={"razon_social": "INTRUSA SA DE CV", "nombre_corto": "INTRUSA"},
        )
        assert len(catalogo.companias) == antes


# ── Compañías ──────────────────────────────────────────────────

class TestCompanias:

    def test_lista_las_que_hay(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        r = cliente.get("/api/companias")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_agrega_una_nueva(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        r = cliente.post(
            "/api/companias",
            json={"razon_social": "NUEVA SA DE CV", "nombre_corto": "NUEVA"},
        )
        assert r.status_code == 200
        assert any(c["razon_social"] == "NUEVA SA DE CV" for c in catalogo.companias)

    def test_el_alias_nuevo_ya_se_resuelve(self, cliente, catalogo, sesion):
        """El flujo completo que reporto el usuario: agregar y que el procesador
        devuelva el alias, sin esperar la cache."""
        from core.catalogo import obtener_nombre_compania

        _entrar(cliente, sesion)
        # Se lee ANTES para llenar la cache con el catalogo viejo.
        obtener_nombre_compania("PEMEX")

        cliente.post(
            "/api/companias",
            json={"razon_social": "NUEVA SA DE CV", "nombre_corto": "NUEVA"},
        )
        assert obtener_nombre_compania("NUEVA SA DE CV") == "NUEVA"

    def test_no_permite_razon_social_duplicada(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        antes = len(catalogo.companias)
        r = cliente.post(
            "/api/companias",
            json={"razon_social": "PEMEX", "nombre_corto": "OTRO"},
        )
        assert r.status_code == 409
        assert len(catalogo.companias) == antes

    def test_el_duplicado_detecta_mayusculas_y_espacios(self, cliente, catalogo, sesion):
        """La comparación es normalizada: 'pemex ' es la misma que 'PEMEX'."""
        _entrar(cliente, sesion)
        r = cliente.post(
            "/api/companias",
            json={"razon_social": "  pemex  ", "nombre_corto": "OTRO"},
        )
        assert r.status_code == 409

    def test_razon_social_vacia_es_400(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        r = cliente.post(
            "/api/companias", json={"razon_social": "   ", "nombre_corto": "X"}
        )
        assert r.status_code == 400

    def test_borra_y_el_alias_deja_de_resolverse(self, cliente, catalogo, sesion):
        from core.catalogo import obtener_nombre_compania

        _entrar(cliente, sesion)
        obtener_nombre_compania("PEMEX")            # llena la cache

        assert cliente.delete("/api/companias/PEMEX").status_code == 200
        # Sin alias, cae en la razón social (que ya no existe en la tabla).
        assert obtener_nombre_compania("PEMEX") == "PEMEX"


# ── Activos ────────────────────────────────────────────────────

class TestActivos:

    def test_lista_los_que_hay(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        r = cliente.get("/api/activos")
        assert r.status_code == 200
        assert {a["nombre"] for a in r.json()} == {"KU-A", "PLATAFORMA CAMPECHE"}

    def test_agrega_y_el_procesador_lo_encuentra(self, cliente, catalogo, sesion):
        """El otro bug del mismo tipo: un activo agregado desde la UI no lo
        encontraba `_buscar_activos`, y la solicitud salía incompleta."""
        from core.catalogo import contiene_activo

        _entrar(cliente, sesion)
        contiene_activo("KU-A")                     # llena la cache

        nuevo = "ACTIVO DE EXTRACCION KU MALOOB ZAAP"
        r = cliente.post("/api/activos", json={"nombre": nuevo})
        assert r.status_code == 200
        assert contiene_activo(nuevo)

    def test_no_permite_activo_duplicado(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        antes = len(catalogo.activos)
        r = cliente.post("/api/activos", json={"nombre": "KU-A"})
        assert r.status_code == 409
        assert len(catalogo.activos) == antes

    def test_nombre_vacio_es_400(self, cliente, catalogo, sesion):
        _entrar(cliente, sesion)
        assert cliente.post("/api/activos", json={"nombre": "  "}).status_code == 400

    def test_borra(self, cliente, catalogo, sesion):
        from core.catalogo import contiene_activo

        _entrar(cliente, sesion)
        contiene_activo("KU-A")
        assert cliente.delete("/api/activos/KU-A").status_code == 200
        assert not contiene_activo("KU-A")