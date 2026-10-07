"""
Tests de `core.comandas.repository` SIN la base de datos.

Estos tests importan el modulo de verdad yEjercitan las funciones puras
(`clave_de_usuario`, `_datos_a_comanda`) mas el ENCADO de los filtros que se
mandan a PostgREST.

Por que existen: `tests/test_api_comandas.py` sustituye las funciones del
repository por dobles, asi que el cuerpo de `repository.py` nunca se ejecuta.
Un error de dedo en una linea interior ahi no aparece; solo se descubre cuando
se corre contra Supabase. Uno de esos errores fue `filters=filtos` en vez de
`filters=filtros`, que tardo en salir a la luz contra la base real.

`_get` / `_post` se sustituyen por una grabadora, de modo que se puede
comprobar EXACTAMENTE lo que se le pediria a PostgREST sin hacer ninguna
peticion.
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import core.comandas.repository as repo  # noqa: E402
from core.comandas.parser import Comanda  # noqa: E402


# ── Grabadora de llamadas ──────────────────────────────────────

class Grabadora:
    """Sustituye `_get` y registra lo que se le pidio."""

    def __init__(self, filas=None, http_status=200, http_json=None):
        self.filas = filas or []
        self.llamadas = []
        self.http_status = http_status
        self.http_json = http_json if http_json is not None else []
        self.posts = []

    def _get(self, table, select="*", filters=None, order=None, limit=None):
        self.llamadas.append({
            "table": table, "select": select, "filters": filters,
            "order": order, "limit": limit,
        })
        return self.filas

    def _post(self, table, data):
        self.posts.append({"table": table, "data": data})
        return {"id": 1}

    def _delete(self, table, filters):
        self.llamadas.append({"table": table, "filters": filters, "delete": True})
        return [{"folio": "X"}]

    def install(self, monkeypatch):
        monkeypatch.setattr(repo, "_get", self._get)
        monkeypatch.setattr(repo, "_post", self._post)
        monkeypatch.setattr(repo, "_delete", self._delete)
        return self


# ── Identidad ──────────────────────────────────────────────────

class TestClaveDeUsuario:

    def test_usa_el_username_no_el_email(self):
        """`subido_por` guarda el username. El login acepta email O username,
        asi que con el email las comandas del usuario serian invisibles para el."""
        clave = repo.clave_de_usuario({"username": "erika", "email": "erika@x.com"})
        assert clave == "erika"

    def test_normaliza_a_minusculas(self):
        assert repo.clave_de_usuario({"username": "Erika"}) == "erika"
        assert repo.clave_de_usuario({"username": "  Erika  "}) == "erika"

    def test_sin_username_es_error(self):
        """Nunca devolver una cadena vacia: eso seria consultar `ilike.`, que
        PostgREST interpreta como 'cualquiera' y devolveria las comandas de
        todos los usuarios."""
        for usuario in ({}, {"username": ""}, {"username": "   "}, {"username": None}):
            with pytest.raises(repo.ErrorComandas):
                repo.clave_de_usuario(usuario)


# ── Filtros ────────────────────────────────────────────────────

class TestFiltros:

    def test_siempre_filtran_por_usuario(self):
        filtros = repo._filtro_usuario("erika")
        assert filtros == {"subido_por": "ilike.erika"}

    def test_ilike_y_no_eq(self):
        """Hay filas historicas que la app de Streamlit guardo sin normalizar a
        minusculas. Con `eq` quedarian invisibles y el usuario 'perderia'
        historial."""
        assert "ilike.erika" in repo._filtro_usuario("erika").values()

    def test_fecha_exacta(self):
        filtros = repo._filtro_usuario("erika", {"fecha_registro": "eq.2026-10-07"})
        assert filtros["fecha_registro"] == "eq.2026-10-07"

    def test_folio_exacto(self):
        filtros = repo._filtro_usuario("erika", {"folio": "eq.OCT001"})
        assert filtros["folio"] == "eq.OCT001"


# ── listar / obtener ───────────────────────────────────────────

class TestListar:

    def test_pide_las_columnas_correctas(self, monkeypatch):
        g = Grabadora([]).install(monkeypatch)
        repo.listar({"username": "erika"}, "2026-10-07")
        assert len(g.llamadas) == 1
        assert g.llamadas[0]["table"] == "comandas"
        # `datos` es el JSONB con todo el contenido.
        assert "datos" in g.llamadas[0]["select"]

    def test_filtra_por_usuario_y_fecha(self, monkeypatch):
        g = Grabadora([]).install(monkeypatch)
        repo.listar({"username": "erika"}, "2026-10-07")
        filtros = g.llamadas[0]["filters"]
        assert filtros["subido_por"] == "ilike.erika"
        assert filtros["fecha_registro"] == "eq.2026-10-07"

    def test_ordena_por_folio(self, monkeypatch):
        filas = [
            {"folio": "OCT003", "datos": {"comanda": "OCT003", "pax": 3}},
            {"folio": "OCT001", "datos": {"comanda": "OCT001", "pax": 1}},
            {"folio": "OCT002", "datos": {"comanda": "OCT002", "pax": 2}},
        ]
        Grabadora(filas).install(monkeypatch)
        resultado = repo.listar({"username": "erika"}, "2026-10-07")
        assert [c.comanda for c in resultado] == ["OCT001", "OCT002", "OCT003"]

    def test_sin_filas_devuelve_lista_vacia(self, monkeypatch):
        Grabadora([]).install(monkeypatch)
        assert repo.listar({"username": "erika"}, "2026-10-07") == []

    def test_obtener_una_concreta(self, monkeypatch):
        filas = [{"folio": "OCT001", "datos": {"comanda": "OCT001", "pax": 7}}]
        g = Grabadora(filas).install(monkeypatch)
        c = repo.obtener({"username": "erika"}, "2026-10-07", "OCT001")
        assert c is not None and c.pax == 7
        assert g.llamadas[0]["filters"]["folio"] == "eq.OCT001"

    def test_obtener_inexistente_devuelve_none(self, monkeypatch):
        Grabadora([]).install(monkeypatch)
        assert repo.obtener({"username": "erika"}, "2026-10-07", "NOPE") is None


# ── Conversion de filas ────────────────────────────────────────

class TestDatosAComanda:

    def test_usa_el_jsonb(self):
        fila = {
            "folio": "OCT001",
            "datos": {
                "comanda": "OCT001", "horario": "06:00", "compania": "COTEMAR",
                "destino": "ABKATUN A", "pax": 12, "transporte": "GANGWAY",
                "menu_1": 12, "menu_2": 0, "tipo": "VIANDA", "observaciones": "COMIDA",
            },
        }
        c = repo._datos_a_comanda(fila)
        assert (c.comanda, c.compania, c.destino, c.pax) == \
            ("OCT001", "COTEMAR", "ABKATUN A", 12)
        assert c.observaciones == "COMIDA"

    def test_se_reconstruye_si_datos_no_es_dict(self):
        """Si `datos` viniera nulo, se usa la columna suelta en vez de perder
        la fila entera."""
        c = repo._datos_a_comanda({"folio": "OCT009", "datos": None})
        assert c.comanda == "OCT009"

    def test_numeros_que_vienen_como_texto(self):
        c = repo._datos_a_comanda(
            {"datos": {"comanda": "X", "pax": "25", "menu_1": "25", "menu_2": ""}}
        )
        assert c.pax == 25 and c.menu_1 == 25 and c.menu_2 == 0

    def test_numeros_ilegibles_no_rompen(self):
        c = repo._datos_a_comanda(
            {"datos": {"comanda": "X", "pax": "muchos", "menu_1": None, "menu_2": 3}}
        )
        assert c.pax == 0 and c.menu_1 == 0 and c.menu_2 == 3

    def test_campos_faltantes_no_rompen(self):
        c = repo._datos_a_comanda({"datos": {"comanda": "X"}})
        assert c.horario == "" and c.compania == "" and c.tipo == "VIANDA"


# ── Fechas ─────────────────────────────────────────────────────

class TestFechasDisponibles:

    def test_usa_la_rpc_si_existe(self, monkeypatch):
        """Con RPC: un solo POST y el DISTINCT lo hace Postgres."""
        llamadas = []

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return [{"fecha_registro": "2026-10-07"},
                        {"fecha_registro": "2026-07-03"},
                        {"fecha_registro": "2026-10-07"}]

        def _post_rpc(url, headers=None, json=None, timeout=None):
            llamadas.append(url)
            return _R()

        monkeypatch.setattr(repo.httpx, "post", _post_rpc)
        g = Grabadora([]).install(monkeypatch)

        fechas = repo.fechas_disponibles({"username": "erika"})
        assert llamadas, "no llamo a la RPC"
        assert fechas == ["2026-10-07", "2026-07-03"], "no dedujo ni ordeno"
        assert g.llamadas == [], "no deberia consultar la tabla si la RPC responde"

    def test_cae_a_la_tabla_si_la_rpc_no_existe(self, monkeypatch):
        """La RPC es una migracion opcional. Si no esta, la pantalla tiene que
        funcionar igual."""

        class _R:
            status_code = 404

        monkeypatch.setattr(
            repo.httpx, "post",
            lambda url, **kw: _R(),
        )
        g = Grabadora([
            {"fecha_registro": "2026-07-03"},
            {"fecha_registro": "2026-10-07"},
            {"fecha_registro": "2026-07-03"},
        ]).install(monkeypatch)

        fechas = repo.fechas_disponibles({"username": "erika"})
        assert fechas == ["2026-10-07", "2026-07-03"]
        assert g.llamadas[0]["select"] == "fecha_registro", "trajo la fila entera"
        assert g.llamadas[0]["order"] == "fecha_registro.desc"


# ── Escritura ──────────────────────────────────────────────────

class TestUpsert:

    def _c(self, folio="OCT001", pax=1):
        return Comanda(folio, "06:00", "COTEMAR", "ABKATUN A", pax, "GANGWAY",
                       pax, 0, "VIANDA", "COMIDA")

    def test_payload_con_las_columnas_de_la_tabla(self, monkeypatch):
        c = self._c()
        fila = repo._payload("erika", "2026-10-07", c)
        assert set(fila) == set(repo.COLUMNAS_UPSERT)
        assert fila["folio"] == "OCT001"
        assert fila["subido_por"] == "erika"
        assert fila["fecha_registro"] == "2026-10-07"
        assert fila["datos"]["comanda"] == "OCT001"

    def test_lote_homogeneo(self, monkeypatch):
        """PostgREST devuelve 400 si las filas del lote tienen claves
        distintas. El constructor garantiza que no pase."""
        comandas = [self._c(f"CMN{i:03d}", pax=i + 1) for i in range(5)]
        for c in comandas:
            assert set(repo._payload("erika", "2026-10-07", c)) == set(repo.COLUMNAS_UPSERT)

    def test_comandas_vacias_no_hacen_nada(self):
        assert repo.upsert_masivo({"username": "erika"}, "2026-10-07", []) == \
            {"guardadas": 0, "folios": []}

    def test_el_conflict_includes_las_tres_columnas(self, monkeypatch):
        """El `on_conflict` DEBE llevar las tres columnas. Con solo dos, el
        folio de un usuario pisaria el de otro: los folios se numeran por
        destino, no por persona."""
        capturado = {}

        class _R:
            status_code = 201

            @staticmethod
            def json():
                return []

        def _post(url, headers=None, json=None, timeout=None):
            capturado["url"] = url
            capturado["headers"] = headers
            capturado["json"] = json
            return _R()

        monkeypatch.setattr(repo.httpx, "post", _post)
        repo.upsert_masivo({"username": "erika"}, "2026-10-07", [self._c()])

        assert "on_conflict=folio,subido_por,fecha_registro" in capturado["url"]
        assert "resolution=merge-duplicates" in capturado["headers"]["Prefer"]

    def test_un_solo_post_para_todas_las_comandas(self, monkeypatch):
        """B2 de la app Streamlit: hacia un POST por comanda. Aqui uno solo."""
        llamadas = []

        class _R:
            status_code = 201

            @staticmethod
            def json():
                return []

        def _post(url, headers=None, json=None, timeout=None):
            llamadas.append(len(json))
            return _R()

        monkeypatch.setattr(repo.httpx, "post", _post)
        repo.upsert_masivo({"username": "erika"}, "2026-10-07",
                           [self._c(f"CMN{i:03d}", i + 1) for i in range(18)])

        assert len(llamadas) == 1, f"hizo {len(llamadas)} POST para 18 comandas"
        assert llamadas[0] == 18

    def test_lotes_partidos_si_hay_muchas(self, monkeypatch):
        """El payload no puede crecer sin limite."""
        llamadas = []

        class _R:
            status_code = 201

            @staticmethod
            def json():
                return []

        monkeypatch.setattr(
            repo.httpx, "post",
            lambda url, headers=None, json=None, timeout=None:
            (llamadas.append(len(json)), _R())[1],
        )
        repo.upsert_masivo({"username": "erika"}, "2026-10-07",
                           [self._c(f"CMN{i:04d}", 1) for i in range(450)])
        assert len(llamadas) == 3, f"450 comandas en {len(llamadas)} lotes"
        assert sum(llamadas) == 450

    def test_409_dice_que_falta_el_indice(self, monkeypatch):
        """Sin el indice unico, PostgREST responde 409. El mensaje tiene que
        decir que hacer, no solo el codigo."""

        class _R:
            status_code = 409
            text = "duplicate key"

        monkeypatch.setattr(
            repo.httpx, "post",
            lambda url, **kw: _R(),
        )
        with pytest.raises(repo.ErrorComandas) as exc:
            repo.upsert_masivo({"username": "erika"}, "2026-10-07", [self._c()])
        assert "indice unico" in str(exc.value)
        assert "003_comandas.sql" in str(exc.value)


# ── Borrar ─────────────────────────────────────────────────────

class TestBorrar:

    def test_filtra_por_usuario_antes_de_borrar(self, monkeypatch):
        """Un DELETE sin filtro por usuario borraria las comandas de otro."""
        g = Grabadora().install(monkeypatch)
        assert repo.borrar({"username": "erika"}, "2026-10-07", "OCT001") is True
        filtros = g.llamadas[0]["filters"]
        assert filtros["subido_por"] == "ilike.erika"
        assert filtros["folio"] == "eq.OCT001"
        assert filtros["fecha_registro"] == "eq.2026-10-07"

    def test_no_existe_no_borra(self, monkeypatch):
        class G(Grabadora):
            def _delete(self, table, filters):
                return []

        G().install(monkeypatch)
        assert repo.borrar({"username": "erika"}, "2026-10-07", "NOPE") is False
