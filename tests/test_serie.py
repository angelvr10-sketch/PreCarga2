"""core/comandas/serie.py — la serie diaria de comandas por barco.

La mayoria son funciones puras: filas de la tabla `comandas` dentro, un
diccionario de series fuera. Se fijan con `hoy` explicito para que no dependan
de la fecha en que corran.
"""
from datetime import date, timedelta
from pathlib import Path
import re

import pytest

from core.comandas.serie import (
    BARCO_POR_USUARIO,
    BARCOS,
    clasificar_barco,
    serie_diaria,
    ventana,
)

HOY = date(2026, 10, 6)


def fila(usuario: str, fecha: str) -> dict:
    """Una fila de `comandas`, con solo lo que la serie lee."""
    return {"fecha_registro": fecha, "subido_por": usuario}


class TestClasificarBarco:
    def test_erika_es_rpx(self):
        assert clasificar_barco("erika") == "RPX"

    def test_pablodg_es_rpx(self):
        # Hoy no tiene comandas, pero si las subiera tienen que caer en RPX.
        assert clasificar_barco("pablodg") == "RPX"

    def test_luise_es_cpz(self):
        assert clasificar_barco("luise") == "CPZ"

    @pytest.mark.parametrize("escrito", ["PabloDG", "pablodg", "PABLODG", "  pablodg  "])
    def test_el_mapa_no_depende_del_uso_de_mayusculas(self, escrito):
        """`usuarios` guarda 'PabloDG' pero `comandas.subido_por` guarda 'pablodg'.

        Es el mismo tropiezo de siempre: si la comparacion fuera sensible a
        mayusculas, las comandas de PabloDG caerian en `sin_asignar` sin avisar.
        """
        assert clasificar_barco(escrito) == "RPX"

    @pytest.mark.parametrize("desconocido", ["admin", "jbl", "usuario de prueba", "", None])
    def test_usuario_desconocido_no_adivina(self, desconocido):
        """Un usuario fuera del mapa devuelve None, NUNCA un barco por defecto.

        Atribuir sus comandas al barco equivocado en silencio es peor que decir
        "no se cual es": el dato falso se ve igual que el verdadero.
        """
        assert clasificar_barco(desconocido) is None

    def test_espacios_al_rededor_no_cuentan(self):
        assert clasificar_barco("  erika  ") == "RPX"

    def test_los_dos_barcos_del_dashboard_son_este_par(self):
        assert BARCOS == ("RPX", "CPZ")

    def test_todo_usuario_del_mapa_apunta_a_un_barco_conocido(self):
        """Si alguien agrega un barco al mapa, tiene que existir en BARCOS.

        Un barco que no este en la tupla se contaria pero no se podria dibujar, y
        la serie perderia esas comandas sin avisar.
        """
        for usuario, barco in BARCO_POR_USUARIO.items():
            assert barco in BARCOS, f"{usuario} apunta a un barco que no existe: {barco}"

    def test_las_claves_del_mapa_estan_en_minusculas(self):
        """Una clave con mayusculas no la encontraria `clasificar_barco`."""
        for clave in BARCO_POR_USUARIO:
            assert clave == clave.lower(), f"la clave {clave!r} deberia estar en minusculas"


class TestVentana:
    def test_termina_hoy_y_empieza_hace_dias_menos_uno(self):
        f = ventana(30, HOY)
        assert len(f) == 30
        assert f[-1] == "2026-10-06"
        assert f[0] == "2026-09-07"

    def test_va_de_mas_viejo_a_mas_reciente(self):
        f = ventana(7, HOY)
        assert f == sorted(f)
        assert f[0] == "2026-09-30"

    def test_siempre_devuelve_tantos_dias_como_se_piden(self):
        """El eje X del grafico alinea las dos series: si una viniera mas corta,
        la comparacion dia a dia estaria desfasada sin que se note."""
        assert len(ventana(1, HOY)) == 1
        assert len(ventana(365, HOY)) == 365

    def test_cruza_el_cambio_de_ano(self):
        f = ventana(10, date(2026, 1, 3))
        assert f[0] == "2025-12-25"
        assert f[-1] == "2026-01-03"

    def test_cruza_el_bisiesto(self):
        f = ventana(3, date(2028, 3, 1))
        assert f == ["2028-02-28", "2028-02-29", "2028-03-01"]

    @pytest.mark.parametrize("pedido,esperado", [(0, 1), (-5, 1), (400, 365)])
    def test_recorta_los_extremos(self, pedido, esperado):
        """El mismo recorte que `_agregar_ultimos_dias`, para que las dos graficas
        del dashboard compartan el selector de periodo sin romper."""
        assert len(ventana(pedido, HOY)) == esperado


class TestSerieDiaria:
    def test_cuenta_por_dia_y_barco(self):
        s = serie_diaria(
            [
                fila("erika", "2026-10-06"),
                fila("erika", "2026-10-06"),
                fila("luise", "2026-10-06"),
                fila("erika", "2026-10-05"),
            ],
            3,
            HOY,
        )
        assert s["rpx"] == [0, 1, 2]
        assert s["cpz"] == [0, 0, 1]

    def test_el_ultimo_dia_de_la_serie_es_hoy(self):
        s = serie_diaria([], 5, HOY)
        assert s["dias"][-1] == "2026-10-06"
        assert s["dias"][0] == "2026-10-02"

    def test_las_tres_sumas_cuadran_con_el_total(self):
        """El invariante de la grafica: RPX + CPZ + sin_asignar = total.

        Si esto no cuadra, el grafico muestra una suma que no es el total y nadie
        se da cuenta: las cifras siguen pareciendo cifras.
        """
        s = serie_diaria(
            [
                fila("erika", "2026-10-06"),
                fila("luise", "2026-10-05"),
                fila("admin", "2026-10-05"),      # fuera del mapa
                fila("otro", "2026-10-04"),      # fuera del mapa
                fila("erika", "2026-01-01"),     # fuera de la ventana
            ],
            7,
            HOY,
        )
        assert sum(s["rpx"]) == 1
        assert sum(s["cpz"]) == 1
        assert s["sin_asignar"] == 2
        assert s["total"] == 4
        assert sum(s["rpx"]) + sum(s["cpz"]) + s["sin_asignar"] == s["total"]

    def test_lo_fuera_de_la_ventana_no_cuenta(self):
        s = serie_diaria(
            [fila("erika", "2026-10-06"), fila("erika", "2025-01-01")],
            3,
            HOY,
        )
        assert s["total"] == 1

    def test_las_comandas_sin_barco_no_se_pierden(self):
        """No es lo mismo 'no hay comandas' que 'no sabemos de que barco son'.

        Lo primero se grafica como 0; lo segundo tiene que avisar, o el dia
        aparece como un hueco sin explicar.
        """
        s = serie_diaria([fila("admin", "2026-10-06")], 3, HOY)
        assert s["rpx"] == [0, 0, 0]
        assert s["cpz"] == [0, 0, 0]
        assert s["sin_asignar"] == 1
        assert s["total"] == 1

    def test_sin_asignar_es_total_de_la_ventana_no_una_serie(self):
        """El frontend solo lo usa para el aviso, asi que no viene por dia."""
        s = serie_diaria(
            [fila("admin", "2026-10-06"), fila("admin", "2026-10-05")], 3, HOY
        )
        assert s["sin_asignar"] == 2

    def test_vacio_devuelve_ceros_y_no_none(self):
        s = serie_diaria([], 30, HOY)
        assert s["rpx"] == [0] * 30
        assert s["cpz"] == [0] * 30
        assert s["sin_asignar"] == 0
        assert s["total"] == 0

    def test_acepta_la_fecha_con_hora_si_viene(self):
        """`fecha_registro` es texto. Si alguna vez trae timestamp, los 10
        primeros caracteres siguen siendo el dia."""
        s = serie_diaria(
            [{"fecha_registro": "2026-10-06T08:30:00", "subido_por": "erika"}], 3, HOY
        )
        assert s["rpx"] == [0, 0, 1]

    @pytest.mark.parametrize("basura", [
        {},
        {"fecha_registro": None, "subido_por": "erika"},
        {"fecha_registro": "no-es-fecha", "subido_por": "erika"},
        {"fecha_registro": "", "subido_por": "erika"},
    ])
    def test_una_fila_sucia_no_tumba_la_grafica(self, basura):
        """Una fila sin fecha utilizable se ignora, no revienta. El dashboard no
        puede quedarse en blanco porque un registro raro entro en la tabla."""
        s = serie_diaria([basura, fila("erika", "2026-10-06")], 3, HOY)
        assert s["total"] == 1

    def test_una_comanda_con_fecha_pero_sin_dueño_cuenta_como_sin_asignar(self):
        """Caso aparte del anterior porque NO es basura: tiene fecha, asi que es
        una comanda real de la ventana. Lo que le falta es el barco, y eso va a
        `sin_asignar` para que el frontend avise, en vez de desaparecer del
        grafico como si fuera un dia sin actividad.
        """
        s = serie_diaria(
            [{"fecha_registro": "2026-10-06", "subido_por": None}, fila("erika", "2026-10-06")],
            3,
            HOY,
        )
        assert s["total"] == 2
        assert s["sin_asignar"] == 1
        assert s["rpx"] == [0, 0, 1]
        assert s["cpz"] == [0, 0, 0]

    def test_el_mismo_dia_de_dos_usuarios_no_se_pisa(self):
        s = serie_diaria(
            [fila("erika", "2026-10-06"), fila("luise", "2026-10-06")], 1, HOY
        )
        assert s["rpx"] == [1]
        assert s["cpz"] == [1]
        assert s["total"] == 2

    def test_la_ventana_no_mira_hacia_al_futuro(self):
        """La ventana termina HOY, asi que una comanda de manana no se cuenta
        todavia. Si alguien subiera un reporte con fecha futura, no debe entrar
        en la serie de hoy ni ensuciar el total."""
        s = serie_diaria(
            [fila("erika", "2026-10-06"), fila("erika", "2026-10-20")], 7, HOY
        )
        assert s["total"] == 1
        assert s["rpx"] == [0, 0, 0, 0, 0, 0, 1]


class TestContraLosDatosReales:
    """Lo que se comprobo en la base antes de escribir esto.

    No consulta Supabase: son los numeros que se leyeron una vez, para que si
    mañana cambia el mapa alguien vea que el test esta describiendo algo viejo.
    """

    def test_lo_que_hay_en_la_tabla_hoy(self):
        # 5,545 comandas; solo dos usuarios suben. LuisE (CPZ) dejo el 2026-09-11
        # y erika (RPX) sigue; por eso en la ventana de 30 dias CPZ sale plano.
        assert BARCO_POR_USUARIO == {"erika": "RPX", "pablodg": "RPX", "luise": "CPZ"}

    def test_la_ventana_de_30_dias_abarca_29_dias(self):
        s = ventana(30, date(2026, 10, 6))
        assert timedelta(days=len(s) - 1).days == 29
        assert s[-1] == "2026-10-06"


# ── Consistencia con el frontend ────────────────────────────────

RAIZ = Path(__file__).resolve().parent.parent
COMPONENTE = RAIZ / "frontend" / "src" / "components" / "dashboard" / "grafica-comandas.tsx"
DASHBOARD = RAIZ / "frontend" / "src" / "routes" / "dashboard.tsx"
TIPOS_STATS = RAIZ / "frontend" / "src" / "types" / "index.ts"


def _serie_frontend() -> dict[str, str]:
    """El mapa `{clave: label}` que declara la constante SERIES del componente."""
    fuente = COMPONENTE.read_text(encoding="utf-8")
    bloque = re.search(r"const SERIES = \[(.*?)\]\s*as const", fuente, re.S)
    assert bloque, "No se encontro la constante SERIES en el componente"
    return {
        clave: label
        for clave, label in re.findall(r"key:\s*'([a-z]+)',\s*label:\s*'([A-Z]+)'", bloque.group(1))
    }


@pytest.mark.skipif(not COMPONENTE.is_file(), reason="No hay frontend en este checkout")
class TestConsistenciaConElFrontend:
    """El backend y el frontend son dos archivos en dos lenguajes que no se ven
    entre si en caliente. Esto fija lo que tienen que decir lo mismo.

    Es el mismo tipo de test que `test_consistencia_roles.py`, y por el mismo
    motivo: en F5 el frontend offering menos de lo que el backend permitia fallo
    en silencio y solo se noto cuando alguien lo uso.
    """

    def test_las_series_del_frontend_son_los_barcos_del_backend(self):
        assert _serie_frontend() == {"rpx": "RPX", "cpz": "CPZ"}

    def test_ninguna_clave_de_la_serie_esta_ausente_en_el_backend(self):
        """Si el backend dejara de exponer una serie, el `dataKey` daria `undefined`
        y la grafica dibujaria una linea en cero SIN avisar. Eso es peor que que
        la serie no exista."""
        respuesta = serie_diaria([], 3, HOY)
        for clave in _serie_frontend():
            assert clave in respuesta, f"El backend no devuelve la serie '{clave}'"

    def test_el_titulo_de_la_grafica_no_promete_una_serie_que_no_existe(self):
        fuente = COMPONENTE.read_text(encoding="utf-8")
        for label in _serie_frontend().values():
            assert f"'{label}'" in fuente, f"El componente ya no menciona {label}"

    def test_la_grafica_se_inserta_debajo_de_altas_vs_bajas(self):
        """Lo pidio el usuario explicitamente: la de comandas va DESPUES de
        Altas vs Bajas y ANTES de Solicitudes Recientes."""
        fuente = DASHBOARD.read_text(encoding="utf-8")
        i_altas = fuente.find("Altas vs Bajas ·")
        i_comandas = fuente.find("<GraficaComandasPorBarco")
        assert i_comandas != -1, "La grafica de comandas no esta en el dashboard"
        assert i_altas != -1
        assert i_comandas > i_altas, "La grafica de comandas tiene que ir despues de Altas vs Bajas"

    def test_la_grafica_comparte_el_periodo_del_selector(self):
        """Si usara un periodo propio, las dos graficas compararian ventanas
        distintas y la comparacion entre ellas seria falsa."""
        fuente = DASHBOARD.read_text(encoding="utf-8")
        assert "dias={periodo}" in fuente and "periodoLabel={periodoLabel}" in fuente


class TestTarjetasDelDashboard:
    """Alta Generadas y Bajas Procesadas se pausaron el 2026-10-06 para dejarle
    el lugar a Total Comandas. Se conservan comentadas, no borradas, asi que este
    test avisa si alguien las quita de verdad."""

    @pytest.fixture(autouse=True)
    def _fuente(self):
        self.dashboard = DASHBOARD.read_text(encoding="utf-8")

    def test_altas_y_bajas_siguen_comentadas(self):
        assert "'altas_generadas'" in self.dashboard, "La tarjeta de Altas desaparecio del todo"
        assert "'bajas_procesadas'" in self.dashboard, "La tarjeta de Bajas desaparecio del todo"
        # Comentadas: la linea existe pero no como elemento de la lista.
        assert "altas_generadas" not in self._activas()
        assert "bajas_procesadas" not in self._activas()

    def test_total_comandas_esta_activa(self):
        assert "total_comandas" in self._activas()

    def test_el_tipo_de_las_stats_declara_total_comandas(self):
        """Sin esto, `stats.total_comandas` no compilaria y la tarjeta saldria
        con '—' sin que se note por que."""
        fuente = TIPOS_STATS.read_text(encoding="utf-8")
        bloque = re.search(r"interface DashboardStats\s*\{(.*?)\n\}", fuente, re.S)
        assert bloque and "total_comandas" in bloque.group(1)

    def test_el_backend_also_trae_total_comandas(self):
        from routers.api_data import router as _  # noqa: F401  (importa main)
        fuente = (RAIZ / "routers" / "api_data.py").read_text(encoding="utf-8")
        assert '"total_comandas": total_comandas()' in fuente

    def _bloque_statcards(self) -> str:
        """Solo el arreglo `statCards`, no todo el archivo.

        Hace falta acotarlo: un `re.findall` sobre el archivo entero tambien
        encuentra las series de 'Altas vs Bajas' (`{ key: 'rpxAltas', ...`) y
        cuenta 8 tarjetas en vez de 4.
        """
        m = re.search(r"const statCards[^=]*=\s*\[(.*?)\n\]", self.dashboard, re.S)
        assert m, "No se encontro el arreglo statCards"
        return m.group(1)

    def _activas(self) -> list[str]:
        """Las claves de tarjeta que de verdad se pintan.

        Se descartan las lineas comentadas, porque un `findall` sobre el bloque
        tambien lee `// { key: 'altas_generadas', ... }` y contaria tarjetas que
        no existen. Es justo la confusion que este archivo tiene que evitar.
        """
        lineas = self._bloque_statcards().splitlines()
        vivas = [ln for ln in lineas if not ln.strip().startswith("//")]
        return re.findall(r"\{ key: '(\w+)'", "\n".join(vivas))

    def test_la_rejilla_no_lleva_un_numero_de_columnas_fijo(self):
        """La anchura sale de cuantas tarjetas haya, no de un `lg:grid-cols-5`
        escrito a mano: con 5 tarjetas caben 5 columnas, y pausando dos se
        quedaban dos columnas vacias a la derecha."""
        assert "COLUMNAS_POR_TARJETA[statCards.length]" in self.dashboard, (
            "La rejilla deberia derivar las columnas de statCards.length. "
            "Si vuelve a un numero fijo, se queda el hueco al pausar tarjetas."
        )

    def test_cuantas_tarjetas_hay(self):
        """Fijado a proposito: son 4 porque se pausaron Altas y Bajas y se sumo
        Total Comandas. Si esto cambia, el aviso de la tarjeta tiene que cambiar
        con el."""
        self._bloque_statcards()  # por lo menos confirma que se encuentra el bloque
        assert self._activas() == [
            "total_solicitudes",
            "total_movimientos",
            "total_companias",
            "total_comandas",
        ]

    def test_hay_columnas_definidas_para_todas_las_tarjetas_activas(self):
        """El fallo silencioso de este patron.

        `COLUMNAS_POR_TARJETA[n] ?? 'lg:grid-cols-4'` no lanza error si falta una
        clave: cae al respaldo y las tarjetas se reparten en 4 columnas sin que
        nadie se entere. Al agregar o quitar una tarjeta, hay que agregar aqui su
        entrada.
        """
        bloque = re.search(
            r"const COLUMNAS_POR_TARJETA[^=]*=\s*\{(.*?)\}", self.dashboard, re.S
        )
        assert bloque, "No se encontro COLUMNAS_POR_TARJETA"
        definidas = {int(n) for n in re.findall(r"^\s*(\d+):", bloque.group(1), re.M)}
        activas = len(self._activas())
        assert activas in definidas, (
            f"Hay {activas} tarjetas activas pero COLUMNAS_POR_TARJETA solo "
            f"define {sorted(definidas)}. Agrega {activas}: 'lg:grid-cols-{activas}', "
            f"o las tarjetas se van a repartir en el valor de respaldo."
        )

    def test_las_clases_existen_literales_en_el_fuente(self):
        """Tailwind extrae las clases leyendo el fuente. Una clase construida por
        concatenacion (`lg:grid-cols-${n}`) no aparece en ninguna parte del
        archivo, no se genera, y en produccion la clase no existe. Por eso los
        valores van escritos enteros."""
        bloque = re.search(
            r"const COLUMNAS_POR_TARJETA[^=]*=\s*\{(.*?)\}", self.dashboard, re.S
        )
        assert bloque
        # Ninguna linea del mapa puede depender de una interpolacion.
        for linea in bloque.group(1).splitlines():
            if ":" in linea:
                assert "${" not in linea, f"clase dinamica, Tailwind no la genera: {linea.strip()!r}"