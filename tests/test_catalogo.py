"""
core/catalogo.py — el catalogo de companias y activos.

── EL BUG QUE ESTA SUITE ATRAPA ─────────────────────────────────────────

La UI (pantalla de Companias y de Activos) escribia en Supabase. El procesador
leia `lib/companias.csv`. Eran dos almacenes y nadie los sincronizaba, asi que
toda alta hecha desde la app era invisible para el Excel generado:

    IXT-06102026-0278   razonsocial = 'MICOPERI DE MEXICO SA DE CV'
                        alias guardado por el usuario: MICOPERI
                        lo que ponia en la celda E8: 'MICOPERI DE MEXICO SA DE CV'

Los tests falsean `core.supabase_db.leer_companias_supabase` y
`leer_activos_supabase` para NO tocar Supabase. Ademas se verifica contra las
tablas reales que la razon social que reporto el usuario este en la de companias:
si alguien la borrara de la base, esta suite debe enterarse, porque entonces el
arreglo del codigo no serviria de nada.
"""
import ast
import os
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# El `.env` se carga ANTES de importar `core.supabase_db`, y en el mismo orden que
# usa `main.py`. Es importante: `SUPABASE_URL` y `BASE` se calculan AL IMPORTAR el
# modulo, asi que si el entorno se carga despues, `BASE` queda con la URL vacia
# (`/rest/v1`) y los tests de datos reales fallan con "Request URL is missing an
# http:// protocol" en vez de saltarse.
from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=RAIZ / ".env")

import core.catalogo as catalogo  # noqa: E402

RAZON_REAL = "MICOPERI DE MEXICO SA DE CV"
ALIAS_REAL = "MICOPERI"
ACTIVO_REAL = "ACTIVO DE EXTRACCION KU MALOOB ZAAP"


def _codigo_sin_comentarios(ruta: Path) -> str:
    """El codigo de un archivo, sin docstrings ni comentarios.

    Se usa `ast` en vez de contar comillas a mano: el docstring de `catalogo`
    explica el bug y menciona los dos CSV a proposito, asi que buscar 'csv' en el
    texto plano daria un falso positivo siempre. `ast` si distingue codigo de
    documentacion, y si el archivo no parsea, revienta aqui en vez de dar un
    resultado silenciosamente equivocado.
    """
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        # Los docstrings son la primera sentencia de modulo, funcion o clase.
        cuerpo = getattr(nodo, "body", None)
        if cuerpo and isinstance(cuerpo[0], ast.Expr) and isinstance(
            cuerpo[0].value, ast.Constant
        ) and isinstance(cuerpo[0].value.value, str):
            del cuerpo[0]
    return ast.unparse(arbol)


@pytest.fixture(autouse=True)
def _sin_cache(monkeypatch):
    """Cada test arranca con la cache limpia.

    Sin esto el orden de ejecucion decidia el resultado: un test que carga el
    catalogo deja el indice en memoria y el siguiente lo lee sin tocar Supabase,
    asi que un cambio en el doble de prueba no se veria. Falla de forma
    intermitente y es dificil de leer.
    """
    catalogo.invalidar_cache()
    yield
    catalogo.invalidar_cache()


@pytest.fixture
def companias(monkeypatch):
    """Las filas de la tabla `companias`, en memoria."""
    filas = [
        {"razon_social": RAZON_REAL, "nombre_corto": ALIAS_REAL},
        {"razon_social": "MICOPERI SRL", "nombre_corto": ALIAS_REAL},
        {"razon_social": "PEMEX", "nombre_corto": "PEMEX"},
        {"razon_social": "DIAVAZ CONSTRUCTORA SA DE CV", "nombre_corto": "DIAVAZ"},
        # Sin alias: tiene que devolver la razón social tal cual.
        {"razon_social": "SIN ALIAS SA DE CV", "nombre_corto": ""},
    ]
    llamadas = []

    def _leer():
        llamadas.append(1)
        return filas

    monkeypatch.setattr(catalogo, "leer_companias_supabase", _leer)
    return filas, llamadas


@pytest.fixture
def activos(monkeypatch):
    """`leer_activos_supabase` devuelve STRINGS, no filas. Es su firma real."""
    lista = ["PLATAFORMA CAMPECHE", ACTIVO_REAL, "KU-A"]

    llamadas = []

    def _leer():
        llamadas.append(1)
        return list(lista)

    monkeypatch.setattr(catalogo, "leer_activos_supabase", _leer)
    return lista, llamadas


class TestAliasDeCompania:

    def test_el_caso_que_reporto_el_usuario(self, companias):
        """La razón social concreta de IXT-06102026-0278."""
        assert catalogo.obtener_nombre_compania(RAZON_REAL) == ALIAS_REAL

    def test_una_compania_mas_se_resuelve_igual(self, companias):
        assert catalogo.obtener_nombre_compania("PEMEX") == "PEMEX"
        assert catalogo.obtener_nombre_compania("DIAVAZ CONSTRUCTORA SA DE CV") == "DIAVAZ"

    @pytest.mark.parametrize("variante", [
        RAZON_REAL,
        RAZON_REAL.lower(),
        "  MICOPERI DE MEXICO SA DE CV  ",
        "micoperi de mexico sa de cv ",
    ])
    def test_no_le_importa_las_mayusculas_ni_los_espacios(self, companias, variante):
        """Las razones sociales llegan de OCR y de captura manual. Una razon social
        que se escribio con espacios de mas no puede perder su alias."""
        assert catalogo.obtener_nombre_compania(variante) == ALIAS_REAL

    def test_razon_social_inexistente_devuelve_ella_misma(self, companias):
        """El documento se genera igual, solo sin abreviar. Fallar aqui dejaria al
        usuario sin Excel, que es peor que un nombre largo en la celda."""
        assert catalogo.obtener_nombre_compania("NO ESTA EN LA LISTA SA DE CV") == \
            "NO ESTA EN LA LISTA SA DE CV"

    @pytest.mark.parametrize("vacio", ["", "   ", None])
    def test_razon_social_vacia_no_reventas(self, companias, vacio):
        assert catalogo.obtener_nombre_compania(vacio) == ""

    def test_sin_alias_devuelve_la_razon_social(self, companias):
        """Una fila con `nombre_corto` vacio no puede devolver cadena vacia: se
        quedaria la celda E8 en blanco en un documento firmado."""
        assert catalogo.obtener_nombre_compania("SIN ALIAS SA DE CV") == "SIN ALIAS SA DE CV"

    def test_no_adivina_un_prefijo_similar(self, companias):
        """'MICOPERI DE MEXICO SA DE CV' y 'MICOPERI SRL' comparten prefijo y las
        dos tienen alias MICOPERI, asi que este caso no distingue. Se prueba con
        una que SOLO se parece: debe devolverla tal cual, no el alias de otra."""
        assert catalogo.obtener_nombre_compania("MICROPEL SA DE CV") == "MICROPEL SA DE CV"

    def test_existe_es_normalizado(self, companias):
        assert catalogo.obtener_nombre_compania_existe(RAZON_REAL)
        assert catalogo.obtener_nombre_compania_existe("  " + RAZON_REAL.lower() + "  ")
        assert not catalogo.obtener_nombre_compania_existe("NO ESTA SA DE CV")

    def test_existe_es_falso_para_vacio(self, companias):
        assert not catalogo.obtener_nombre_compania_existe("")
        assert not catalogo.obtener_nombre_compania_existe(None)


class TestActivos:

    def test_el_activo_que_agrego_la_ui_ahora_se_encuentra(self, activos):
        """El que faltaba: estaba en Supabase y el procesador no lo veia, asi que
        la solicitation salia con 'Activo solicitante no encontrado'."""
        assert catalogo.contiene_activo(ACTIVO_REAL)

    def test_rechaza_un_activo_que_no_existe(self, activos):
        assert not catalogo.contiene_activo("PLATAFORMA INVENTADA")

    def test_no_le_importa_las_mayusculas(self, activos):
        assert catalogo.contiene_activo(ACTIVO_REAL.lower())

    def test_leer_activos_devuelve_los_nombres(self, activos):
        assert ACTIVO_REAL in catalogo.leer_activos()
        assert len(catalogo.leer_activos()) == 3

    def test_no_reventa_con_un_activo_vacio(self, monkeypatch):
        """Un nombre en blanco no es un activo, y `contiene_activo('')` daria
        True para todo lo que este en blanco."""
        monkeypatch.setattr(
            catalogo, "leer_activos_supabase", lambda: ["KU-A", "", "   ", None]
        )
        catalogo.invalidar_cache()
        assert catalogo.leer_activos() == ["KU-A"]
        assert not catalogo.contiene_activo("")


class TestCache:

    def test_no_pregunta_a_supabase_dos_veces(self, companias):
        """El procesador genera un Excel por PDF. Sin cache seria un request a
        Supabase por archivo, con la latencia que eso significa en produccion."""
        _, llamadas = companias
        for _ in range(50):
            catalogo.obtener_nombre_compania(RAZON_REAL)
        assert len(llamadas) == 1

    def test_activos_tambien_se_cachean(self, activos):
        _, llamadas = activos
        for _ in range(50):
            catalogo.leer_activos()
        assert len(llamadas) == 1

    def test_invalidar_fuerza_a_releer(self, companias):
        _, llamadas = companias
        catalogo.obtener_nombre_compania(RAZON_REAL)
        catalogo.invalidar_cache(companias=True)
        catalogo.obtener_nombre_compania(RAZON_REAL)
        assert len(llamadas) == 2

    def test_invalidar_una_no_toca_la_otra(self, companias, activos):
        """`companias=False, activos=True` es lo que llama el endpoint de activos:
        no debe tirar la cache de companias y provocar un request de mas."""
        _, llamadas_comp = companias
        _, llamadas_act = activos
        catalogo.obtener_nombre_compania(RAZON_REAL)
        catalogo.leer_activos()
        catalogo.invalidar_cache(companias=False, activos=True)
        catalogo.obtener_nombre_compania(RAZON_REAL)
        catalogo.leer_activos()
        assert len(llamadas_comp) == 1, "Se pidio companias de mas"
        assert len(llamadas_act) == 2, "No se recargo activos"

    def test_el_alias_nuevo_se_ve_sin_esperar(self, companias, monkeypatch):
        """El flujo que reporta el usuario: agrega la compania y genera el PDF.

        Sin `invalidar_cache()` en el alta, tendria que esperar el TTL. Con ella,
        la siguiente lectura ve el cambio.
        """
        filas, _ = companias
        catalogo.obtener_nombre_compania(RAZON_REAL)      # llena la cache

        # Simula el POST /api/companias: agrega y luego invalida.
        filas.append({"razon_social": "NUEVA SA DE CV", "nombre_corto": "NUEVA"})
        catalogo.invalidar_cache(companias=True)

        assert catalogo.obtener_nombre_compania("NUEVA SA DE CV") == "NUEVA"

    def test_ttl_no_es_cero(self):
        """Un TTL de 0 equivale a no tener cache: cada PDF haria un request."""
        assert catalogo.CATALOGO_TTL_SEGUNDOS > 0


class TestContraLaBaseReal:
    """Verifica contra Supabase que los datos que sostienen el arreglo existen.

    Si alguien borrara la razón social del reporte, el código del arreglo
    seguiría dando verde y la app volvería a fallar en silencio. Estos tests lo
    detectan.

    El `.env` lo carga `main.py`; estos tests no importan `main` (no lo
    necesitan), así que se carga aquí. Si no hay `.env` o no hay red, se saltan
    en vez de fallar: una suite de red no debe romper el CI de una máquina sin
    credenciales.
    """

    @pytest.fixture(autouse=True)
    def _supabase(self):
        pytest.importorskip("httpx", reason="httpx no instalado")

        import core.supabase_db as db

        # Se comprueba `SUPABASE_URL`, no `BASE`: `BASE` siempre es una cadena no
        # vacia (aunque le falte el protocolo, si el .env no se cargo), asi que
        # comprobarlo daria verde y luego reventaria la peticion.
        if not db.SUPABASE_URL.startswith("http"):
            pytest.skip("Sin SUPABASE_URL con protocolo en el entorno")

        try:
            yield
        finally:
            catalogo.invalidar_cache()

    def test_la_razon_social_del_reporte_existe_en_la_tabla(self):
        from core.supabase_db import leer_companias_supabase

        filas = leer_companias_supabase()
        encontradas = [
            c for c in filas
            if (c.get("razon_social") or "").strip().upper() == RAZON_REAL.upper()
        ]
        assert encontradas, f"'{RAZON_REAL}' no esta en la tabla companias"
        assert (encontradas[0].get("nombre_corto") or "").strip() == ALIAS_REAL

    def test_el_activo_del_reporte_existe_en_la_tabla(self):
        from core.supabase_db import leer_activos_supabase

        nombres = [(a or "").strip().upper() for a in leer_activos_supabase()]
        assert ACTIVO_REAL.upper() in nombres

    def test_la_tabla_tiene_mas_companias_que_el_csv(self):
        """Guarda contra una regresion a 'el CSV es la fuente': si volveran a
        coincidir los conteos, es que alguien volvio a leer el archivo de 25."""
        from core.supabase_db import leer_companias_supabase

        assert len(leer_companias_supabase()) > 25

    def test_la_solicitud_reportada_muestra_el_alias(self):
        """El caso exacto del reporte, contra los datos reales.

        IXT-06102026-0278 tiene `compania` = 'MICOPERI DE MEXICO SA DE CV' (la
        copia que se horneó al procesar, antes de que existiera el alias) y
        `razonsocial` igual. Lo que debe verse en el listado es 'MICOPERI'.
        """
        from core.supabase_db import _get

        filas = _get(
            "solicitudes",
            select="numero,compania,razonsocial",
            filters={"numero": "eq.IXT-06102026-0278"},
        )
        assert filas, "La solicitud del reporte ya no existe"
        fila = filas[0]
        assert (fila.get("razonsocial") or "").strip() == RAZON_REAL
        # La copia sigue con el nombre largo: es justo el bug, y por eso el
        # listado NO puede leerla.
        assert (fila.get("compania") or "").strip() == RAZON_REAL
        assert catalogo.nombre_para_listado(fila) == ALIAS_REAL

    def test_la_mayoria_de_las_solicitudes_no_tienen_razonsocial(self):
        """Documenta por que el caso 2 del resolver existe.

        Si algun dia todas las filas tuvieran `razonsocial`, se podria simplificar
        el resolver a una sola busqueda. Este test avisa cuando eso pase, para que
        el atajo sea una decision y no un descuido.
        """
        from core.supabase_db import _get_all

        filas = _get_all("solicitudes", select="razonsocial")
        sin_rs = sum(1 for f in filas if not (f.get("razonsocial") or "").strip())
        assert sin_rs > 0, (
            "Todas las solicitudes tienen ya `razonsocial`. El caso 2 de "
            "nombre_para_listado (resolver por `compania`) ya no se necesita y "
            "puede simplificarse."
        )


class TestNombreParaListado:
    """Como se ve la compañía en los LISTADOS (dashboard, Altas, Bajas).

    ── EL BUG QUE ESTA SUITE ATRAPA ─────────────────────────────────────────

    Se reportó que en los listados seguía apareciendo
    'MICOPERI DE MEXICO SA DE CV' en vez de 'MICOPERI'.

    No era un alias mal cargado: era un dato VIEJO. `solicitudes.comania` guarda
    el alias que se resolvió AL PROCESAR EL PDF, así que una solicitud procesada
    antes de que existiera el alias guarda el nombre largo para siempre.
    IXT-06102026-0278 es de las 29 solicitudes (de 670) que sí tienen
    `razonsocial`.

    Por eso los listados tienen que resolver en LECTURA contra el catálogo vivo,
    no leer la copia. Agregar el alias cambia lo que se ve sin reprocesar nada.
    """

    def test_el_caso_que_reporto_el_usuario(self, companias):
        fila = {
            "numero": "IXT-06102026-0278",
            "compania": RAZON_REAL,        # la copia vieja, con el nombre largo
            "razonsocial": RAZON_REAL,
        }
        assert catalogo.nombre_para_listado(fila) == ALIAS_REAL

    def test_una_fila_vieja_sin_razonsocial_tambien_se_abrevia(self, companias):
        """641 de 670 solicitudes NO tienen `razonsocial`: se procesaron antes de
        que existiera la columna. En esas, `compania` guarda el nombre largo de
        origen y sirve como clave de búsqueda."""
        fila = {"numero": "CME-170726-0001", "compania": RAZON_REAL, "razonsocial": None}
        assert catalogo.nombre_para_listado(fila) == ALIAS_REAL

    def test_una_fila_ya_abreviada_se_respeta(self, companias):
        """Si `compania` ya es el alias de otra razón social, no hay que
        "arreglarla": devolverla larga o buscarle otro alias sería inventar."""
        fila = {"numero": "CME-170726-0002", "compania": "JBL", "razonsocial": None}
        assert catalogo.nombre_para_listado(fila) == "JBL"

    def test_razonsocial_manda_sobre_compania(self, companias):
        """Cuando existen las dos, manda `razonsocial`: es el dato de origen.
        `compania` es la copia, y la copia puede estar vieja."""
        fila = {
            "compania": "ALIAS VIEJO",       # lo que quedo al procesar
            "razonsocial": RAZON_REAL,        # el dato real
        }
        assert catalogo.nombre_para_listado(fila) == ALIAS_REAL

    def test_una_razonsocial_sin_alias_se_devuelve_entera(self, companias):
        """No hay alias para esta: se muestra el nombre, no una cadena vacía."""
        fila = {"compania": "DESCONOCIDA SA DE CV", "razonsocial": "DESCONOCIDA SA DE CV"}
        assert catalogo.nombre_para_listado(fila) == "DESCONOCIDA SA DE CV"

    @pytest.mark.parametrize("fila", [
        {},
        {"compania": "", "razonsocial": ""},
        {"compania": None, "razonsocial": None},
        {"razonsocial": None},
    ])
    def test_filas_vacias_no_reventan(self, companias, fila):
        """El listado tiene que poder pintar aunque la fila venga incompleta."""
        assert catalogo.nombre_para_listado(fila) == ""

    def test_es_indiferente_a_mayusculas(self, companias):
        fila = {"compania": "  micoperi de mexico sa de cv  ", "razonsocial": None}
        assert catalogo.nombre_para_listado(fila) == ALIAS_REAL

    def test_no_adivina_una_compania_que_solo_se_parece(self, companias):
        """'MICROPEL' se parece a 'MICOPERI...' pero no es ella. La comparación es
        exacta a propósito: un alias equivocado en un documento firmado es peor que
        no abreviar."""
        fila = {"compania": "MICROPEL SA DE CV", "razonsocial": "MICROPEL SA DE CV"}
        assert catalogo.nombre_para_listado(fila) == "MICROPEL SA DE CV"


class TestElAliasSigueAlCatalogo:
    """El listado no guarda copia: si cambia el alias, cambia lo que se ve.

    Es la diferencia entre arreglar el caso de hoy y arreglarlo de verdad. Con la
    copia (lo que habia), cambiar un alias mañana exigiría reprocesar 670 PDFs.
    """

    def test_cambiar_el_alias_cambia_el_listado(self, companias):
        filas, _ = companias
        antes = catalogo.nombre_para_listado({"razonsocial": RAZON_REAL})
        assert antes == ALIAS_REAL

        # El usuario corrige el alias desde la pantalla de Compañías.
        for f in filas:
            if f["razon_social"] == RAZON_REAL:
                f["nombre_corto"] = "MICOPERI-MX"
        catalogo.invalidar_cache(companias=True)

        assert catalogo.nombre_para_listado({"razonsocial": RAZON_REAL}) == "MICOPERI-MX"

    def test_agregar_el_alias_tambien_cambia_el_listado(self, companias):
        """El caso real: la fila se procesó SIN alias y el alias se agregó después.
        Con la copia, lo guardado seguiría siendo el nombre largo para siempre."""
        filas, _ = companias
        filas[:] = [f for f in filas if f["razon_social"] != RAZON_REAL]
        catalogo.invalidar_cache(companias=True)

        fila = {"compania": RAZON_REAL, "razonsocial": RAZON_REAL}
        assert catalogo.nombre_para_listado(fila) == RAZON_REAL, \
            "sin alias, la razón social se muestra tal cual"

        filas.append({"razon_social": RAZON_REAL, "nombre_corto": ALIAS_REAL})
        catalogo.invalidar_cache(companias=True)

        assert catalogo.nombre_para_listado(fila) == ALIAS_REAL, \
            "el alias agregado tiene que verse sin reprocesar el PDF"


class TestLosListadosLoUsan:
    """Que los TRES listados resuelvan, y no solo la función auxiliar.

    Es un test de FUENTES a proposito: los tres leian `r["compania"]` directo y
    funcionaban, con datos viejos. Nada fallaba; solo se veia el nombre largo. Por
    eso hace falta comprobar el texto de la llamada, no solo el comportamiento de
    `nombre_para_listado`.
    """

    @pytest.mark.parametrize("ruta,nombre", [
        ("core/procesador.py", "listar_solicitudes_xlsx"),   # dashboard y /altas
        ("core/db.py", "listar_solicitudes_db"),
        ("core/db.py", "listar_bajas_db"),                   # pantalla de Bajas
    ])
    def test_el_listado_llama_al_resolver(self, ruta, nombre):
        """Que la LLAMADA exista en el código, no en la documentación.

        La primera versión de este test buscaba el texto `nombre_para_listado` en
        el cuerpo de la función, y daba verde en falso: los tres docstrings
        mencionan el nombre para explicar por qué se llama. Al reintroducir el bug
        (volver a leer `r["compania"]`), dos de los tres tests siguieron pasando
        porque la palabra estaba en el docstring.

        Por eso se usa `ast`: se busca una llamada real, dentro del cuerpo, y el
        docstring no cuenta.
        """
        arbol = ast.parse(Path(RAIZ / ruta).read_text(encoding="utf-8"))
        funcion = None
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef) and nodo.name == nombre:
                funcion = nodo
                break
        assert funcion is not None, f"No se encontro {nombre} en {ruta}"

        llamadas = {
            n.func.id
            for n in ast.walk(funcion)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        }
        assert "nombre_para_listado" in llamadas, (
            f"{nombre} sigue leyendo la columna `compania` (la copia vieja del "
            f"alias) en vez de resolverlo contra el catálogo. Llamadas que hace: "
            f"{sorted(llamadas)}"
        )


def _select_declarado(ruta: Path, nombre: str) -> str:
    """El valor de la clave `"select"` que pide la consulta, dentro de esa función.

    Se lee con `ast` y no buscando texto, por dos razones:

      - `ast.unparse` (que usa `_codigo_sin_comentarios`) reescribe las comillas, así
        que comparar con `"select": "*"` daría falso por el estilo, no el contenido;
      - el `select` no siempre es un kwarg de `_get`. En `listar_solicitudes_xlsx`
        va dentro de un dict que luego se pasa como `filters=query_params`, y un
        test que solo mirara los kwargs no lo encontraría.

    Busca en los dos sitios: kwargs de una llamada a `_get` y cualquier dict
    literal con clave `"select"`.
    """
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == nombre:
            # 1. Como kwarg de la llamada a _get.
            for n in ast.walk(nodo):
                if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "_get":
                    for kw in n.keywords:
                        if kw.arg == "select" and isinstance(kw.value, ast.Constant):
                            return str(kw.value.value)
            # 2. Como clave de un dict literal (el caso de query_params).
            for n in ast.walk(nodo):
                if isinstance(n, ast.Dict):
                    for k, v in zip(n.keys, n.values):
                        if (isinstance(k, ast.Constant) and k.value == "select"
                                and isinstance(v, ast.Constant)):
                            return str(v.value)
    return ""


class TestLosListadosLoUsan2:
    """Continuacion de `TestLosListadosLoUsan`, en su propia clase para que las
    funciones auxiliares queden al nivel del modulo."""

    def test_el_select_trae_razonsocial(self):
        """Sin `razonsocial` en el SELECT, el resolver no puede usar la fuente de
        origen y todo depende de la copia. Las dos funciones de `core/db.py` lo
        declaran de forma explicita."""
        for nombre in ("listar_solicitudes_db", "listar_bajas_db"):
            select = _select_declarado(RAIZ / "core" / "db.py", nombre)
            assert select, f"No se encontro el `select` de la llamada a _get en {nombre}"
            assert "razonsocial" in select, (
                f"{nombre} pide '{select}': sin `razonsocial` el resolver se queda "
                f"solo con la copia vieja de `compania`, y los listados vuelven a "
                f"mostrar el nombre largo."
            )

    def test_listar_solicitudes_xlsx_usa_select_estrella(self):
        """`listar_solicitudes_xlsx` pide `select=*`, asi que `razonsocial` llega
        sola. Se fija para que nadie cambie a una lista de columnas y se lleve el
        campo por delante sin querer."""
        select = _select_declarado(RAIZ / "core" / "procesador.py", "listar_solicitudes_xlsx")
        assert select.strip() == "*", (
            f"listar_solicitudes_xlsx pide select='{select}' en vez de '*'. Si se "
            f"reduce a una lista de columnas, `razonsocial` deja de llegar y el "
            f"resolver se queda solo con la copia vieja."
        )


class TestElCsvNoSeUsa:

    def test_catalogo_no_abre_ningun_csv(self):
        """Guarda el bug original a futuro: leer el CSV era la causa, asi que si
        vuelve a aparecer una lectura de archivo, el problema regresa.

        Se examina el CODIGO, no el texto entero: el docstring de este modulo
        explica el bug y menciona los dos CSV a proposito, asi que buscar "csv"
        en todo el archivo daria un falso positivo siempre.

        Es un test de FUENTES a proposito: `leer_companias` devolvia datos
        correctos y aun asi el alias no llegaba, porque leia el almacen equivocado.
        """
        codigo = _codigo_sin_comentarios(Path(catalogo.__file__))

        assert "csv" not in codigo.lower(), "El catalogo volvio a leer el CSV"
        assert "RUTA_COMPANIAS" not in codigo
        assert "RUTA_ACTIVOS" not in codigo
        assert "open(" not in codigo, "El catalogo no debe abrir archivos"

    def test_config_ya_no_expone_las_rutas_del_csv(self):
        """Si alguien las reexporta, el import de `RUTA_ACTIVOS` vuelve a funcionar
        y el modulo parece que si usa el CSV sin que lo haga de verdad."""
        import core.config as config

        assert not hasattr(config, "RUTA_COMPANIAS")
        assert not hasattr(config, "RUTA_ACTIVOS")

    def test_core_init_no_exporta_las_funciones_del_csv(self):
        import core

        assert not hasattr(core, "leer_companias")
        assert not hasattr(core, "guardar_companias")
        assert not hasattr(core, "guardar_activos")