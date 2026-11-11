"""
Tests del router de comandas.

NO tocan Supabase ni la red. Dos cosas se sustituyen por dobles de prueba:

  - las funciones de `core.comandas.repository` (listar, obtener,
    fechas_disponibles, upsert_masivo, diagnostico) por un almacen en memoria;
  - `get_current_user` y el par de cuota de `core.auth` por funciones locales.

Lo que se prueba es la CAPA HTTP: quien puede entrar, que devuelve cada codigo de
estado, que la cuota de descargas se descuenta cuando toca y que un lector no
genera lo que no le toca.

Ojo con esto: los tests monkeypatchean `routers.api_comandas`, no `core.auth` ni
`core.comandas.repository`, para no alterar el comportamiento de los demas
routers de precarga2.
"""
import io
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import main  # noqa: E402
from core.comandas.parser import Comanda  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPORTE_REAL = FIXTURES / "ComandaAlimentos.pdf"


# ── Almacen en memoria ─────────────────────────────────────────

class AlmacenFalso:
    """Sustituye a `core.comandas.repository` sin tocar la base de datos.

    Mantiene las filas con la misma forma que la tabla `comandas`, para que los
    filtros de `subido_por` se comporten como en Postgres.
    """

    def __init__(self):
        self.filas = []            # [{folio, subido_por, fecha_registro, datos}]
        self.escrituras = 0        # quantas veces se llamo upsert_masivo
        self.fallos_upsert = None

    # ── API que usa el router ──
    def listar(self, usuario, fecha_iso):
        from core.comandas.repository import _datos_a_comanda
        u = usuario["username"].lower()
        comandas = [
            _datos_a_comanda(f) for f in self.filas
            if f["subido_por"] == u and f["fecha_registro"] == fecha_iso
        ]
        comandas.sort(key=lambda c: c.comanda)
        return comandas

    def obtener(self, usuario, fecha_iso, folio):
        for c in self.listar(usuario, fecha_iso):
            if c.comanda == folio:
                return c
        return None

    def fechas_disponibles(self, usuario):
        u = usuario["username"].lower()
        fechas = {f["fecha_registro"] for f in self.filas if f["subido_por"] == u}
        return sorted(fechas, reverse=True)

    def upsert_masivo(self, usuario, fecha_iso, comandas):
        from core.comandas.repository import ErrorComandas
        if self.fallos_upsert:
            raise ErrorComandas(self.fallos_upsert)
        self.escrituras += 1
        u = usuario["username"].lower()
        ahora = datetime.now().isoformat()

        # Upsert por (folio, subido_por, fecha_registro).
        por_clave = {
            (f["folio"], f["subido_por"], f["fecha_registro"]): i
            for i, f in enumerate(self.filas)
        }
        for c in comandas:
            clave = (c.comanda, u, fecha_iso)
            fila = {
                "folio": c.comanda, "subido_por": u, "fecha_registro": fecha_iso,
                "datos": c.a_dict(), "updated_at": ahora,
            }
            if clave in por_clave:
                self.filas[por_clave[clave]] = fila
            else:
                por_clave[clave] = len(self.filas)
                self.filas.append(fila)

        return {"guardadas": len(comandas), "folios": [c.comanda for c in comandas]}

    def diagnostico(self, usuario):
        u = usuario["username"].lower()
        mias = [f for f in self.filas if f["subido_por"] == u]
        return {
            "usuario": u, "comandas_en_tabla": len(self.filas),
            "mis_comandas": len(mias), "mis_fechas": len({f["fecha_registro"] for f in mias}),
            "ultimas_fechas": [], "error": None,
        }

    # ── Escritura de una comanda suelta (crear / modificar / borrar) ──
    #
    # Reproducen las reglas de `core/comandas/repository.py` que importan para la
    # capa HTTP: el duplicado es un error de uso (no un 500), y el filtro por
    # dueño se aplica SIEMPRE, aunque el folio y la fecha coincidan.

    def crear(self, usuario, fecha_iso, comanda):
        from core.comandas.repository import ErrorComandaDuplicada
        u = usuario["username"].lower()
        if any(f["folio"] == comanda.comanda and f["subido_por"] == u
               and f["fecha_registro"] == fecha_iso for f in self.filas):
            raise ErrorComandaDuplicada(
                f"Ya existe la comanda {comanda.comanda} del {fecha_iso}"
            )
        self.escrituras += 1
        self.filas.append({
            "folio": comanda.comanda, "subido_por": u, "fecha_registro": fecha_iso,
            "datos": comanda.a_dict(), "updated_at": datetime.now().isoformat(),
        })
        return comanda

    def actualizar(self, usuario, fecha_iso, folio, comanda):
        u = usuario["username"].lower()
        for i, f in enumerate(self.filas):
            if (f["folio"] == folio and f["subido_por"] == u
                    and f["fecha_registro"] == fecha_iso):
                self.escrituras += 1
                self.filas[i] = {
                    **f, "datos": comanda.a_dict(),
                    "updated_at": datetime.now().isoformat(),
                }
                return True
        return False

    def borrar(self, usuario, fecha_iso, folio):
        u = usuario["username"].lower()
        antes = len(self.filas)
        self.filas = [
            f for f in self.filas
            if not (f["folio"] == folio and f["subido_por"] == u
                    and f["fecha_registro"] == fecha_iso)
        ]
        if len(self.filas) == antes:
            return False
        self.escrituras += 1
        return True

    # ── API que usa el router ──
    def serie_diaria_barcos(self, dias, hoy=None):
        """La serie global del dashboard, sobre las filas del almacen.

        Delega en la funcion pura de `core.comandas.serie`, igual que el
        repositorio real: aqui lo que se prueba es la CAPA HTTP, y el recorte por
        fecha ya esta probado en tests/test_serie.py con `hoy` explicito.

        Se le pasan TODAS las filas, sin filtrar por usuario: este endpoint es la
        excepcion documentada al aislamiento, y el almacen tiene que poder
        demostrar que cuenta tambien las de otro.
        """
        from core.comandas.serie import serie_diaria
        return serie_diaria(
            [{"fecha_registro": f["fecha_registro"], "subido_por": f["subido_por"]}
             for f in self.filas],
            dias,
            hoy,
        )

    # ── Utilidades de los tests ──
    def sembrar(self, username, fecha_iso, comandas):
        self.upsert_masivo({"username": username}, fecha_iso, comandas)


@pytest.fixture
def almacen(monkeypatch):
    a = AlmacenFalso()
    import routers.api_comandas as rc
    import core.comandas.repository as repo

    for nombre in ("listar", "obtener", "fechas_disponibles",
                   "upsert_masivo", "diagnostico", "serie_diaria_barcos",
                   "crear", "actualizar", "borrar"):
        monkeypatch.setattr(rc, nombre, getattr(a, nombre))
        monkeypatch.setattr(repo, nombre, getattr(a, nombre))
    return a


@pytest.fixture
def descargas(monkeypatch):
    """Contador de descargas controlable."""
    estado = {"permitido": True, "contadas": 0, "motivo": "sin cuota"}

    def _puede(user):
        return (estado["permitido"], "" if estado["permitido"] else estado["motivo"])

    def _contar(usuario_id):
        estado["contadas"] += 1

    import routers.api_comandas as rc
    monkeypatch.setattr(rc, "puede_descargar", _puede)
    monkeypatch.setattr(rc, "contar_descarga", _contar)
    return estado


@pytest.fixture
def cliente():
    """TestClient con la sesion ya puesta, saltando el login real."""
    with TestClient(main.app) as c:
        yield c


def _sesion(cliente, usuario):
    """Pone una cookie de sesion para `usuario`, SIN tocar Supabase.

    Se falsea `get_current_user`, que es lo unico que el router consulta para
    saber quien es. Nada se escribe en la base de datos: esta suite no debe
    dejar rastro en el proyecto real de Supabase.

    Se sustituye la funcion en el modulo del router, no en `core.auth`, porque
    los demas routers de precarga2 la importan y aqui no se tocan.
    """
    import routers.api_comandas as rc
    rc.get_current_user = lambda request: usuario
    cliente.cookies.set("session", "test-local")


ADMIN = {"id": 1, "username": "admin", "email": "admin@x.com", "rol": "admin",
         "descargas_usadas": 0}
USUARIO = {"id": 2, "username": "erika", "email": "erika@x.com", "rol": "usuario",
           "descargas_usadas": 0}
LECTOR = {"id": 3, "username": "jbl", "email": "jbl@x.com", "rol": "lector",
          "descargas_usadas": 0}


def _comanda(folio="OCT001", destino="ABKATUN A", compania="NORCONTROL",
             pax=1, m1=1, m2=0, obs="COMIDA-VIANDA"):
    return Comanda(folio, "06:00", compania, destino, pax, "GANGWAY", m1, m2,
                   "MORTERA" if "MORTERA" in obs else "VIANDA", obs)


# ── Autorizacion ───────────────────────────────────────────────

class TestAutorizacion:

    @pytest.fixture(autouse=True)
    def _sin_sesion(self, monkeypatch):
        """Por defecto, sin sesion en ningun test de esta clase."""
        import routers.api_comandas as rc
        monkeypatch.setattr(rc, "get_current_user", lambda request: None)

    @pytest.mark.parametrize("ruta", [
        "/api/comandas/fechas",
        "/api/comandas/",
        "/api/comandas/estadisticas",
        "/api/comandas/reporte/estadistico",
        "/api/comandas/reporte/todas",
        "/api/comandas/reporte/mortera",
        "/api/comandas/reporte/vales",
        "/api/comandas/diagnostico",
    ])
    def test_sin_sesion_es_401(self, cliente, almacen, descargas, ruta):
        cliente.cookies.clear()
        r = cliente.get(ruta)
        assert r.status_code == 401, f"{ruta} dejo pasar a un usuario sin sesion"

    def test_importar_sin_sesion_es_401(self, cliente, almacen, descargas):
        cliente.cookies.clear()
        r = cliente.post("/api/comandas/importar", files={"file": ("x.pdf", b"%PDF-1.4")})
        assert r.status_code == 401


# ── Lectura ────────────────────────────────────────────────────

class TestLectura:

    def test_fechas_del_usuario(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        almacen.sembrar("admin", "2026-10-07", [_comanda("OCT001")])
        almacen.sembrar("admin", "2026-07-03", [_comanda("JUL025", destino="YKN")])
        almacen.sembrar("otro", "2026-05-05", [_comanda("MAY001")])

        r = cliente.get("/api/comandas/fechas")
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["fechas"] == ["2026-10-07", "2026-07-03"], (
            "Se colaron fechas de otro usuario, o no se ordenaron al reves"
        )
        assert "2026-05-05" not in cuerpo["fechas"]

    def test_comandas_de_una_fecha(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        almacen.sembrar("admin", "2026-10-07",
                        [_comanda("OCT002"), _comanda("OCT001", pax=2, m1=2)])

        r = cliente.get("/api/comandas/?fecha=2026-10-07")
        assert r.status_code == 200
        c = r.json()
        assert c["total"] == 2
        assert c["total_pax"] == 3
        # Ordenadas por folio.
        assert [x["comanda"] for x in c["comandas"]] == ["OCT001", "OCT002"]

    def test_fecha_por_defecto_es_hoy(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        almacen.sembrar("admin", datetime.now().strftime("%Y-%m-%d"),
                        [_comanda("HOY001")])
        r = cliente.get("/api/comandas/")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_fecha_invalida_es_400(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        assert cliente.get("/api/comandas/?fecha=no-es-fecha").status_code == 400
        assert cliente.get("/api/comandas/?fecha=2026-13-45").status_code == 400

    def test_fecha_vacia_devuelve_lista_vacia(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/?fecha=2026-01-01")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_aislamiento_entre_usuarios(self, cliente, almacen, descargas):
        """Dos usuarios con el mismo folio en fechas distintas no se pisan."""
        _sesion(cliente, USUARIO)
        almacen.sembrar("erika", "2026-10-07", [_comanda("OCT001", pax=5, m1=5)])
        almacen.sembrar("jbl", "2026-10-07", [_comanda("OCT001", pax=99, m1=99)])

        r = cliente.get("/api/comandas/?fecha=2026-10-07")
        assert r.json()["total_pax"] == 5, "Se vio la comanda de otro usuario"


# ── Estadisticas ───────────────────────────────────────────────

class TestEstadisticas:

    def test_sumas_cuadran(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        almacen.sembrar("admin", "2026-10-07", [
            _comanda("OCT001", destino="ABKATUN A", pax=10, m1=10, compania="COTEMAR"),
            _comanda("OCT002", destino="YKN", pax=5, m1=5, compania="SIPCO"),
            _comanda("OCT003", destino="YKN", pax=3, m1=3, m2=1,
                     obs="ALIMENTOS EN MORTERA", compania="COTEMAR"),
        ])

        r = cliente.get("/api/comandas/estadisticas?fecha=2026-10-07")
        assert r.status_code == 200
        e = r.json()

        assert e["total_comandas"] == 3
        assert e["total_alimentos"] == 10 + 5 + 4 == 19
        assert e["total_mortera"] == 4
        assert e["total_viandas"] == 15
        assert sum(e["por_destino"].values()) == 19
        assert sum(e["por_transporte"].values()) == 19
        assert e["por_compania"]["COTEMAR"] == 14

    def test_sin_datos_no_rompe(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/estadisticas?fecha=2026-01-01")
        assert r.status_code == 200
        assert r.json()["total_comandas"] == 0


# ── Importar ───────────────────────────────────────────────────

class TestImportar:

    def _pdf_real(self):
        return REPORTE_REAL.read_bytes() if REPORTE_REAL.is_file() else None

    def test_rechaza_extension_no_pdf(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        r = cliente.post("/api/comandas/importar",
                         files={"file": ("reporte.txt", b"no soy pdf")})
        assert r.status_code == 400
        assert "PDF" in r.json()["detail"]

    def test_rechaza_contenido_falso(self, cliente, almacen, descargas):
        """Extension .pdf pero los bytes no son de un PDF."""
        _sesion(cliente, ADMIN)
        r = cliente.post("/api/comandas/importar",
                         files={"file": ("malo.pdf", b"esto es texto plano")})
        assert r.status_code == 400
        assert "%PDF-" in r.json()["detail"]

    def test_rechaza_vacio(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        r = cliente.post("/api/comandas/importar",
                         files={"file": ("vacio.pdf", b"")})
        assert r.status_code == 400

    def test_pdf_sin_comandas_es_422(self, cliente, almacen, descargas):
        """Un PDF valido que no es reporte de comandas: 422, no 500."""
        _sesion(cliente, ADMIN)
        # PDF minimo valido, sin tablas de comandas.
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, "documento que no es un reporte de comandas")
        c.save()

        r = cliente.post("/api/comandas/importar",
                         files={"file": ("x.pdf", buf.getvalue())})
        assert r.status_code == 422
        assert r.json()["ok"] is False

    @pytest.mark.skipif(not REPORTE_REAL.is_file(), reason="sin el reporte real")
    def test_importa_reporte_real(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        datos = REPORTE_REAL.read_bytes()

        r = cliente.post("/api/comandas/importar",
                         files={"file": ("reporte.pdf", datos)})
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["ok"] is True
        assert c["total"] == 18          # congelado en test_fixtures_reales
        assert c["fecha"] == "2026-07-03"
        assert c["guardadas"] == 18
        assert almacen.escrituras == 1   # UN upsert, no 18 viajes

    @pytest.mark.skipif(not REPORTE_REAL.is_file(), reason="sin el reporte real")
    def test_reimportar_no_duplica(self, cliente, almacen, descargas):
        """Subir dos veces el mismo reporte actualiza, no duplica."""
        _sesion(cliente, ADMIN)
        datos = REPORTE_REAL.read_bytes()

        cliente.post("/api/comandas/importar", files={"file": ("a.pdf", datos)})
        cliente.post("/api/comandas/importar", files={"file": ("a.pdf", datos)})

        total = cliente.get("/api/comandas/?fecha=2026-07-03").json()["total"]
        assert total == 18, f"Reimportar duplico: {total} filas"

    def test_error_de_base_es_500(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        almacen.fallos_upsert = "no hay indice unico"
        buf = io.BytesIO()
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(buf)
        c.setFont("Helvetica", 12)
        c.drawString(72, 700, "NO. COM. HORARIO OCT001 06:00 ABKATUN A 05 GANGWAY 05 00 X")
        c.save()

        r = cliente.post("/api/comandas/importar",
                         files={"file": ("x.pdf", buf.getvalue())})
        # O bien 422 (no.parseo) o bien 500 (fallo al guardar). Lo que NO puede
        # ser es 200 con datos a medias.
        assert r.status_code in (422, 500)
        assert r.json().get("ok") is not True


# ── Escritura de una comanda suelta ────────────────────────────

def _cuerpo(**kwargs):
    """Cuerpo de POST/PUT con todos los campos; cada test cambia uno."""
    datos = {
        "fecha": "2026-10-07",
        "comanda": "NOV001",
        "horario": "06:30",
        "compania": "NORCONTROL",
        "destino": "ABKATUN A",
        "pax": 12,
        "transporte": "GANGWAY",
        "tipo": "VIANDA",
        "observaciones": "COMIDA-VIANDA",
    }
    datos.update(kwargs)
    return datos


class TestCrearComanda:
    """POST /api/comandas/ — la comanda que no viene de ningun PDF."""

    def test_crea_y_aparece_en_la_lista(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.post("/api/comandas/", json=_cuerpo())
        assert r.status_code == 201, r.text
        assert r.json()["ok"] is True
        assert r.json()["comanda"]["comanda"] == "NOV001"

        lista = cliente.get("/api/comandas/?fecha=2026-10-07").json()
        assert lista["total"] == 1
        assert lista["total_pax"] == 12          # menu_1 se copio de pax

    def test_la_fecha_nueva_entra_en_el_selector(self, cliente, almacen, descargas):
        """Sin esto, crear la primera comanda de un dia no dejaria volver a el."""
        _sesion(cliente, USUARIO)
        almacen.filas.clear()
        r = cliente.post("/api/comandas/", json=_cuerpo(fecha="2026-11-05"))
        assert r.status_code == 201, r.text
        assert cliente.get("/api/comandas/fechas").json()["fechas"] == ["2026-11-05"]

    def test_normaliza_folio_y_horario(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.post("/api/comandas/", json=_cuerpo(comanda="nov 002",
                                                        horario="7:5"))
        assert r.status_code == 201, r.text
        c = r.json()["comanda"]
        assert (c["comanda"], c["horario"]) == ("NOV002", "07:05")

    def test_duplicado_es_409_y_no_sobrescribe(self, cliente, almacen, descargas):
        """Crear no puede ser un upsert: un folio repetido no debe pisar la
        comanda que ya estaba."""
        _sesion(cliente, USUARIO)
        almacen.sembrar("erika", "2026-10-07", [_comanda("NOV001", pax=3, m1=3)])

        r = cliente.post("/api/comandas/", json=_cuerpo(pax=99))
        assert r.status_code == 409
        assert "Ya existe" in r.json()["detail"]

        lista = cliente.get("/api/comandas/?fecha=2026-10-07").json()
        assert lista["total"] == 1
        assert lista["total_pax"] == 3, "el 409 igual sobrescribio la comanda"

    def test_el_mismo_folio_de_otro_usuario_si_se_puede(self, cliente, almacen, descargas):
        """Los folios se numeran por destino, no por persona: dos usuarios
        pueden tener el mismo folio el mismo dia."""
        _sesion(cliente, USUARIO)
        almacen.sembrar("jbl", "2026-10-07", [_comanda("NOV001", pax=40, m1=40)])

        r = cliente.post("/api/comandas/", json=_cuerpo(pax=2))
        assert r.status_code == 201, r.text
        # La de erika es la suya, y la de jbl sigue intacta.
        assert cliente.get("/api/comandas/?fecha=2026-10-07").json()["total_pax"] == 2
        assert len(almacen.filas) == 2

    def test_sin_fecha_es_400(self, cliente, almacen, descargas):
        """Las escrituras no asumen 'hoy': una comanda guardada en el dia
        equivocado es peor que un error."""
        _sesion(cliente, USUARIO)
        cuerpo = _cuerpo()
        del cuerpo["fecha"]
        r = cliente.post("/api/comandas/", json=cuerpo)
        assert r.status_code == 400
        assert "fecha" in r.json()["detail"].lower()

    def test_fecha_invalida_es_400(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        assert cliente.post("/api/comandas/",
                            json=_cuerpo(fecha="2026-13-45")).status_code == 400

    @pytest.mark.parametrize("cambio", [
        {"horario": "25:99"},
        {"horario": ""},
        {"tipo": "OTRA"},
        {"transporte": "CAMION"},
        {"pax": -1},
        {"pax": "muchos"},
        {"pax": 0, "menu_1": 0, "menu_2": 0},
        {"compania": ""},
        {"destino": "   "},
        {"comanda": ""},
        {"comanda": "CON ESPACIO@"},
        {"observaciones": "x" * 600},
    ])
    def test_datos_invalidos_son_400(self, cliente, almacen, descargas, cambio):
        _sesion(cliente, USUARIO)
        r = cliente.post("/api/comandas/", json=_cuerpo(**cambio))
        assert r.status_code == 400, f"{cambio} deberia ser 400, fue {r.status_code}"
        assert almacen.filas == [], "se guardo algo con datos invalidos"

    def test_cuerpo_que_no_es_objeto_es_400(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.post("/api/comandas/", json=["NOV001"])
        assert r.status_code == 400

    def test_sin_sesion_es_401(self, cliente, almacen, descargas, monkeypatch):
        import routers.api_comandas as rc
        monkeypatch.setattr(rc, "get_current_user", lambda request: None)
        cliente.cookies.clear()
        assert cliente.post("/api/comandas/", json=_cuerpo()).status_code == 401

    def test_lector_no_crea(self, cliente, almacen, descargas):
        _sesion(cliente, LECTOR)
        r = cliente.post("/api/comandas/", json=_cuerpo())
        assert r.status_code == 403
        assert "crear comandas" in r.json()["detail"]
        assert almacen.filas == []


class TestModificarComanda:
    """PUT /api/comandas/{folio} — corregir una comanda existente."""

    @pytest.fixture(autouse=True)
    def _datos(self, almacen):
        almacen.sembrar("erika", "2026-10-07", [
            _comanda("OCT001", pax=5, m1=5, obs="COMIDA-VIANDA"),
        ])
        almacen.sembrar("jbl", "2026-10-07", [
            _comanda("OCT001", pax=99, m1=99),
        ])

    def test_modifica_los_datos(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.put("/api/comandas/OCT001?fecha=2026-10-07",
                        json=_cuerpo(comanda=None, pax=8, menu_1=8,
                                     compania="COTEMAR", horario="9:15"))
        assert r.status_code == 200, r.text

        c = cliente.get("/api/comandas/?fecha=2026-10-07").json()["comandas"][0]
        assert (c["pax"], c["menu_1"], c["compania"], c["horario"]) == \
            (8, 8, "COTEMAR", "09:15")

    def test_el_folio_no_cambia(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        cliente.put("/api/comandas/OCT001?fecha=2026-10-07",
                    json=_cuerpo(comanda=None, pax=8))
        folios = [f["folio"] for f in almacen.filas if f["subido_por"] == "erika"]
        assert folios == ["OCT001"]

    def test_no_toca_la_comanda_de_otro_usuario(self, cliente, almacen, descargas):
        """Mismo folio, misma fecha, otro dueño: el filtro por usuario manda."""
        _sesion(cliente, USUARIO)
        cliente.put("/api/comandas/OCT001?fecha=2026-10-07",
                    json=_cuerpo(comanda=None, pax=8))

        de_jbl = [f for f in almacen.filas
                  if f["subido_por"] == "jbl" and f["folio"] == "OCT001"]
        assert de_jbl[0]["datos"]["pax"] == 99

    def test_inexistente_es_404(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.put("/api/comandas/NOEXISTE?fecha=2026-10-07",
                        json=_cuerpo(comanda=None))
        assert r.status_code == 404

    def test_fecha_ajena_es_404(self, cliente, almacen, descargas):
        """La comanda existe, pero en otra fecha: no se modifica."""
        _sesion(cliente, USUARIO)
        r = cliente.put("/api/comandas/OCT001?fecha=2026-10-06",
                        json=_cuerpo(comanda=None))
        assert r.status_code == 404

    def test_falta_la_fecha_es_400(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.put("/api/comandas/OCT001", json=_cuerpo(comanda=None))
        assert r.status_code == 400
        assert "fecha" in r.json()["detail"].lower()

    def test_cambiar_el_folio_es_400(self, cliente, almacen, descargas):
        """El folio es llave: para "cambiarlo" hay que borrar y crear."""
        _sesion(cliente, USUARIO)
        r = cliente.put("/api/comandas/OCT001?fecha=2026-10-07",
                        json=_cuerpo(comanda="OTRO1"))
        assert r.status_code == 400
        assert "no se puede cambiar" in r.json()["detail"]

    def test_datos_invalidos_son_400(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.put("/api/comandas/OCT001?fecha=2026-10-07",
                        json=_cuerpo(comanda=None, tipo="NARANJA"))
        assert r.status_code == 400

    def test_lector_no_modifica(self, cliente, almacen, descargas):
        _sesion(cliente, LECTOR)
        r = cliente.put("/api/comandas/OCT001?fecha=2026-10-07",
                        json=_cuerpo(comanda=None, pax=8))
        assert r.status_code == 403
        assert "modificar comandas" in r.json()["detail"]


class TestEliminarComanda:
    """DELETE /api/comandas/{folio} — borrar una comanda de una fecha."""

    @pytest.fixture(autouse=True)
    def _datos(self, almacen):
        almacen.sembrar("erika", "2026-10-07", [
            _comanda("OCT001"), _comanda("OCT002"),
        ])
        almacen.sembrar("jbl", "2026-10-07", [_comanda("OCT001")])

    def test_elimina_la_comanda(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        r = cliente.delete("/api/comandas/OCT001?fecha=2026-10-07")
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

        lista = cliente.get("/api/comandas/?fecha=2026-10-07").json()
        assert [c["comanda"] for c in lista["comandas"]] == ["OCT002"]

    def test_al_borrar_la_ultima_la_fecha_desaparece(self, cliente, almacen, descargas):
        """El frontend vuelve al estado vacio cuando no quedan fechas."""
        _sesion(cliente, USUARIO)
        cliente.delete("/api/comandas/OCT001?fecha=2026-10-07")
        cliente.delete("/api/comandas/OCT002?fecha=2026-10-07")
        assert cliente.get("/api/comandas/fechas").json()["fechas"] == []

    def test_no_borra_la_de_otro_usuario(self, cliente, almacen, descargas):
        """Mismo folio, misma fecha, otro dueño: solo se va la propia."""
        _sesion(cliente, USUARIO)
        r = cliente.delete("/api/comandas/OCT001?fecha=2026-10-07")
        assert r.status_code == 200, r.text

        # La de jbl (mismo folio y fecha) sigue ahi.
        assert any(f["subido_por"] == "jbl" and f["folio"] == "OCT001"
                   for f in almacen.filas)
        assert not any(f["subido_por"] == "erika" and f["folio"] == "OCT001"
                       for f in almacen.filas)

    def test_no_borra_en_una_fecha_que_no_es(self, cliente, almacen, descargas):
        """Sin la fecha correcta no se encuentra la fila: 404, no un borrado."""
        _sesion(cliente, USUARIO)
        r = cliente.delete("/api/comandas/OCT001?fecha=2026-10-06")
        assert r.status_code == 404
        assert len(almacen.filas) == 3

    def test_inexistente_es_404(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        assert cliente.delete(
            "/api/comandas/NOEXISTE?fecha=2026-10-07"
        ).status_code == 404

    def test_falta_la_fecha_es_400(self, cliente, almacen, descargas):
        """Un DELETE sin fecha borraria 'la de hoy' sin que nadie lo pidiera."""
        _sesion(cliente, USUARIO)
        r = cliente.delete("/api/comandas/OCT001")
        assert r.status_code == 400
        assert len(almacen.filas) == 3, "borro algo sin que se pidiera la fecha"

    def test_lector_no_elimina(self, cliente, almacen, descargas):
        _sesion(cliente, LECTOR)
        r = cliente.delete("/api/comandas/OCT001?fecha=2026-10-07")
        assert r.status_code == 403
        assert "eliminar comandas" in r.json()["detail"]
        assert len(almacen.filas) == 3

    def test_sin_sesion_es_401(self, cliente, almacen, descargas, monkeypatch):
        import routers.api_comandas as rc
        monkeypatch.setattr(rc, "get_current_user", lambda request: None)
        cliente.cookies.clear()
        assert cliente.delete(
            "/api/comandas/OCT001?fecha=2026-10-07"
        ).status_code == 401


class TestEscrituraNoDescuentaCuota:
    """Crear, modificar y borrar no generan PDF: no gastan descargas."""

    def test_las_tres_operaciones_cuentan_cero(self, cliente, almacen, descargas):
        descargas["permitido"] = True
        _sesion(cliente, USUARIO)

        cliente.post("/api/comandas/", json=_cuerpo())
        cliente.put("/api/comandas/NOV001?fecha=2026-10-07",
                    json=_cuerpo(comanda=None, pax=4))
        cliente.delete("/api/comandas/NOV001?fecha=2026-10-07")

        assert descargas["contadas"] == 0


# ── Reportes ───────────────────────────────────────────────────

class TestReportes:

    @pytest.fixture(autouse=True)
    def _datos(self, almacen):
        almacen.sembrar("admin", "2026-10-07", [
            _comanda("OCT001", pax=10, m1=10),
            _comanda("OCT002", destino="YKN", pax=5, m1=5, obs="ALIMENTOS EN MORTERA"),
        ])

    def test_reporte_estadistico_es_pdf(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/reporte/estadistico?fecha=2026-10-07")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF-")
        assert "attachment" in r.headers["content-disposition"]
        assert r.headers["cache-control"] == "private, no-store"

    @pytest.mark.parametrize("tipo,paginas", [
        ("todas", 2),
        ("mortera", 2),
        ("vales", 1),
        ("estadistico", 1),
    ])
    def test_paginas_segun_tipo(self, cliente, almacen, descargas, tipo, paginas):
        from pypdf import PdfReader
        _sesion(cliente, ADMIN)
        r = cliente.get(f"/api/comandas/reporte/{tipo}?fecha=2026-10-07")
        assert r.status_code == 200
        assert len(PdfReader(io.BytesIO(r.content)).pages) == paginas

    def test_pdf_individual(self, cliente, almacen, descargas):
        from pypdf import PdfReader
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/reporte/comanda/OCT001?fecha=2026-10-07")
        assert r.status_code == 200
        texto = PdfReader(io.BytesIO(r.content)).pages[0].extract_text()
        assert "OCT001" in texto
        assert "RECIBE ALIMENTOS" in texto

    def test_pdf_individual_inexistente_es_404(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/reporte/comanda/NOEXISTE?fecha=2026-10-07")
        assert r.status_code == 404

    def test_sin_datos_es_404(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/reporte/todas?fecha=2026-01-01")
        assert r.status_code == 404
        assert "No hay comandas" in r.json()["detail"]


# ── Roles ──────────────────────────────────────────────────────

class TestRoles:

    @pytest.fixture(autouse=True)
    def _datos(self, almacen):
        almacen.sembrar("jbl", "2026-10-07", [_comanda("OCT001")])
        almacen.sembrar("erika", "2026-10-07", [_comanda("OCT001")])

    @pytest.mark.parametrize("tipo", ["todas", "mortera", "vales"])
    def test_lector_no_genera_reportes_en_bloque(self, cliente, almacen, descargas, tipo):
        _sesion(cliente, LECTOR)
        r = cliente.get(f"/api/comandas/reporte/{tipo}?fecha=2026-10-07")
        assert r.status_code == 403

    def test_lector_si_puede_ver_el_estadistico(self, cliente, almacen, descargas):
        _sesion(cliente, LECTOR)
        r = cliente.get("/api/comandas/estadisticas?fecha=2026-10-07")
        assert r.status_code == 200

    def test_lector_si_puede_descargar_una_comanda(self, cliente, almacen, descargas):
        _sesion(cliente, LECTOR)
        r = cliente.get("/api/comandas/reporte/comanda/OCT001?fecha=2026-10-07")
        assert r.status_code == 200

    def test_lector_no_entra_al_diagnostico(self, cliente, almacen, descargas):
        _sesion(cliente, LECTOR)
        assert cliente.get("/api/comandas/diagnostico").status_code == 403

    def test_admin_entra_al_diagnostico(self, cliente, almacen, descargas):
        _sesion(cliente, ADMIN)
        assert cliente.get("/api/comandas/diagnostico").status_code == 200

    def test_usuario_normal_no_entra_al_diagnostico(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        assert cliente.get("/api/comandas/diagnostico").status_code == 403

    @pytest.mark.parametrize("tipo", ["todas", "mortera", "vales"])
    def test_usuario_normal_si_genera_reportes(self, cliente, almacen, descargas, tipo):
        """El rol 'usuario' NO es lector: tiene los mismos permisos que admin
        menos el diagnostico.

        Este caso es el que se rompio: el frontend trataba a todo usuario que
        no fuera admin como lector y le ocultaba tres de los cuatro botones,
        aunque el backend se los dejaba generar.
        """
        _sesion(cliente, USUARIO)
        r = cliente.get(f"/api/comandas/reporte/{tipo}?fecha=2026-10-07")
        assert r.status_code == 200, f"rol 'usuario' no pudo generar '{tipo}'"


class TestRolEnLaSesion:
    """`/api/auth/me` tiene que exponer el rol CRUDO, no solo el booleano admin.

    Sin `rol`, el frontend no puede distinguir 'usuario' de 'lector' y acaba
    tratando a los usuarios normales como lectores.

    `/api/auth/me` vive en `routers/api_auth.py` y usa SU propio
    `get_current_user`, asi que hay que falsear tambien ese, no solo el del
    router de comandas.
    """

    @pytest.fixture(autouse=True)
    def _sesion_falsa(self, monkeypatch):
        """`/api/auth/me` no usa `get_current_user`: lee la cookie y consulta
        `get_user_from_token`. Se falsea esa, y se pone una cookie cualquiera."""
        import routers.api_auth as ra

        actual = {"user": None}

        def _desde_token(token):
            return actual["user"] if token else None

        monkeypatch.setattr(ra, "get_user_from_token", _desde_token)
        self._actual = actual
        self.cliente_cookie = "test-token"

    def test_me_incluye_el_rol(self, cliente):
        cliente.cookies.set("session", self.cliente_cookie)
        self._actual["user"] = USUARIO
        r = cliente.get("/api/auth/me")
        assert r.status_code == 200
        assert r.json()["user"]["rol"] == "usuario"

    def test_me_marca_admin_correctamente(self, cliente):
        cliente.cookies.set("session", self.cliente_cookie)
        self._actual["user"] = ADMIN
        cuerpo = cliente.get("/api/auth/me").json()["user"]
        assert cuerpo["rol"] == "admin"
        assert cuerpo["admin"] is True

    def test_me_sigue_devolviendo_admin_booleano(self, cliente):
        """`admin` es lo que lee el resto de la app: no puede desaparecer."""
        cliente.cookies.set("session", self.cliente_cookie)
        self._actual["user"] = USUARIO
        cuerpo = cliente.get("/api/auth/me").json()["user"]
        assert cuerpo["admin"] is False

    def test_rol_de_lector_tambien_viaja(self, cliente):
        cliente.cookies.set("session", self.cliente_cookie)
        self._actual["user"] = LECTOR
        cuerpo = cliente.get("/api/auth/me").json()["user"]
        assert cuerpo["rol"] == "lector"
        assert cuerpo["admin"] is False

    def test_sin_rol_no_rompe_la_respuesta(self, cliente):
        """Un usuario sin `rol` (fila vieja, o creada a mano) no debe tumbar el
        endpoint: `admin` se calcula y el resto de campos viajan igual."""
        cliente.cookies.set("session", self.cliente_cookie)
        self._actual["user"] = {"id": "99", "username": "raro", "email": ""}
        cuerpo = cliente.get("/api/auth/me").json()["user"]
        assert cuerpo["rol"] == ""
        assert cuerpo["admin"] is False


# ── Cuota de descargas (decision D3) ───────────────────────────

class TestCuotaDeDescargas:

    @pytest.fixture(autouse=True)
    def _datos(self, almacen):
        almacen.sembrar("admin", "2026-10-07", [_comanda("OCT001")])

    @pytest.mark.parametrize("ruta", [
        "/api/comandas/reporte/estadistico",
        "/api/comandas/reporte/todas",
        "/api/comandas/reporte/mortera",
        "/api/comandas/reporte/vales",
        "/api/comandas/reporte/comanda/OCT001",
    ])
    def test_cada_descarga_descuenta_una(self, cliente, almacen, descargas, ruta):
        descargas["permitido"] = True
        _sesion(cliente, ADMIN)
        r = cliente.get(f"{ruta}?fecha=2026-10-07")
        assert r.status_code == 200
        assert descargas["contadas"] == 1, f"{ruta} no descontó la descarga"

    def test_sin_cuota_es_402(self, cliente, almacen, descargas):
        descargas["permitido"] = False
        descargas["motivo"] = "Te quedaste sin descargas gratis (30/30)"
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/reporte/todas?fecha=2026-10-07")
        assert r.status_code == 402

    def test_sin_cuota_no_descuenta(self, cliente, almacen, descargas):
        """Si se rechaza, no se cuenta: si no, un usuario bloqueado quemaria
        cuota igual."""
        descargas["permitido"] = False
        _sesion(cliente, ADMIN)
        cliente.get("/api/comandas/reporte/todas?fecha=2026-10-07")
        assert descargas["contadas"] == 0

    def test_lectura_no_descuenta(self, cliente, almacen, descargas):
        """Mirar el dashboard no es descargar."""
        descargas["permitido"] = True
        _sesion(cliente, ADMIN)
        cliente.get("/api/comandas/fechas")
        cliente.get("/api/comandas/?fecha=2026-10-07")
        cliente.get("/api/comandas/estadisticas?fecha=2026-10-07")
        assert descargas["contadas"] == 0

    def test_importar_no_descuenta(self, cliente, almacen, descargas):
        """Subir un reporte tampoco es una descarga."""
        descargas["permitido"] = True
        _sesion(cliente, ADMIN)
        buf = io.BytesIO()
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(buf)
        c.setFont("Helvetica", 12)
        c.drawString(72, 700, "OCT001 06:00 ABKATUN A 05 GANGWAY 05 00 NOTAS")
        c.save()
        cliente.post("/api/comandas/importar", files={"file": ("x.pdf", buf.getvalue())})
        assert descargas["contadas"] == 0

    def test_sin_datos_no_descuenta(self, cliente, almacen, descargas):
        """Pedir un reporte de una fecha sin datos no puede costarle una descarga."""
        descargas["permitido"] = True
        _sesion(cliente, ADMIN)
        r = cliente.get("/api/comandas/reporte/todas?fecha=2026-01-01")
        assert r.status_code == 404
        assert descargas["contadas"] == 0


def _dia_hace(dias: int) -> str:
    """Fecha ISO de hace `dias` dias.

    La serie se pide con `?dias=30`, asi que una fecha fija en el test caduca
    sola al pasar el tiempo. Calculandola desde hoy, el caso sigue midiendo lo
    que quiere medir.
    """
    from datetime import date, timedelta

    from core.comandas.fecha import hoy_iso

    return (date.fromisoformat(hoy_iso()) - timedelta(days=dias)).isoformat()


class TestSerieDeBarcos:
    """GET /api/comandas/serie — la serie diaria por barco del dashboard.

    Es la UNICA lectura de este router que no va por `clave_de_usuario`, porque
    alimenta una tarjeta y una grafica del dashboard, donde todo lo demas ya es
    global. Estos tests fijan ese comportamiento para que no se vuelva un
    descuido: si alguien le pone filtro por usuario, el grafico dejaria de cuadrar
    con la tarjeta y nadie veria por que.
    """

    @pytest.fixture(autouse=True)
    def _datos(self, almacen):
        almacen.sembrar("erika", _dia_hace(2), [_comanda("OCT001"), _comanda("OCT002")])
        almacen.sembrar("erika", _dia_hace(3), [_comanda("OCT003")])
        almacen.sembrar("LuisE", _dia_hace(2), [_comanda("OCT004")])
        almacen.sembrar("PabloDG", _dia_hace(4), [_comanda("OCT005")])

    def test_exige_sesion(self, cliente, almacen, descargas):
        import routers.api_comandas as rc
        rc.get_current_user = lambda request: None
        assert cliente.get("/api/comandas/serie?dias=30").status_code == 401

    @pytest.mark.parametrize("rol", [ADMIN, USUARIO, LECTOR])
    def test_cualquier_rol_autenticado_lo_ve(self, cliente, almacen, descargas, rol):
        """Es un conteo del dashboard, no el documento de un usuario: tambien el
        lector lo ve, igual que ve las demas tarjetas globales."""
        _sesion(cliente, rol)
        assert cliente.get("/api/comandas/serie?dias=30").status_code == 200

    def test_cuenta_las_comandas_de_los_dos_barcos(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        c = cliente.get("/api/comandas/serie?dias=30").json()
        assert sum(c["rpx"]) == 4     # 3 de erika + 1 de PabloDG
        assert sum(c["cpz"]) == 1     # 1 de LuisE
        assert c["total"] == 5

    def test_es_global_y_no_solo_las_mias(self, cliente, almacen, descargas):
        """La razon de la excepcion: la serie de erika incluye lo que subio
        LuisE y PabloDG."""
        _sesion(cliente, USUARIO)
        c = cliente.get("/api/comandas/serie?dias=30").json()
        assert sum(c["cpz"]) == 1, "Se filtraron las comandas de otro usuario"

    def test_las_tres_sumas_cuadran(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        c = cliente.get("/api/comandas/serie?dias=30").json()
        assert sum(c["rpx"]) + sum(c["cpz"]) + c["sin_asignar"] == c["total"]

    def test_devuelve_los_dias_pedidos_mas_la_anticipacion(self, cliente, almacen, descargas):
        """El endpoint devuelve `dias + DIAS_FUTURO`: los 30 de historico intactos
        mas 2 dias hacia adelante, que es lo que pidio el usuario para que el eje
        X no se corte justo en hoy."""
        from core.config import DIAS_FUTURO
        _sesion(cliente, USUARIO)
        for dias in (1, 7, 30, 365):
            c = cliente.get(f"/api/comandas/serie?dias={dias}").json()
            assert len(c["dias"]) == dias + DIAS_FUTURO
            assert len(c["rpx"]) == len(c["cpz"]) == dias + DIAS_FUTURO

    def test_el_uso_de_mayusculas_no_rompe_el_mapa(self, cliente, almacen, descargas):
        """`usuarios` tiene 'PabloDG' y 'LuisE'; `comandas.subido_por` guarda
        minusculas. Sin normalizar, las dos series saldrian vacias sin avisar."""
        _sesion(cliente, USUARIO)
        c = cliente.get("/api/comandas/serie?dias=30").json()
        assert sum(c["rpx"]) > 0 and sum(c["cpz"]) > 0
        assert c["sin_asignar"] == 0

    def test_las_comandas_de_un_usuario_fuera_del_mapa_se_avisan(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        almacen.sembrar("admin", _dia_hace(2), [_comanda("OCT006")])
        c = cliente.get("/api/comandas/serie?dias=30").json()
        assert c["sin_asignar"] == 1
        assert c["total"] == 6

    def test_no_cuenta_descargas(self, cliente, almacen, descargas):
        """Es JSON, no un PDF: no descuenta cuota."""
        _sesion(cliente, USUARIO)
        cliente.get("/api/comandas/serie?dias=30")
        assert descargas["contadas"] == 0

    def test_el_ultimo_dia_de_la_serie_es_dos_dias_adelante(self, cliente, almacen, descargas):
        """La serie no termina hoy: termina dos dias despues, para que se vea el
        espacio de lo que viene. Hoy tiene que seguir estando DENTRO de la
        respuesta, no solo en las series."""
        from datetime import date, timedelta
        from core.comandas.fecha import hoy_iso
        from core.config import DIAS_FUTURO
        _sesion(cliente, USUARIO)
        c = cliente.get("/api/comandas/serie?dias=30").json()
        hoy = hoy_iso()
        esperado = (date.fromisoformat(hoy) + timedelta(days=DIAS_FUTURO)).isoformat()
        assert c["dias"][-1] == esperado
        assert hoy in c["dias"]

    def test_va_de_mas_viejo_a_hoy(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        c = cliente.get("/api/comandas/serie?dias=5").json()
        assert c["dias"] == sorted(c["dias"])

    def test_lo_mas_viejo_del_rango_no_cuenta(self, cliente, almacen, descargas):
        _sesion(cliente, USUARIO)
        almacen.sembrar("erika", "2020-01-01", [_comanda("ANT001"), _comanda("ANT002")])
        c = cliente.get("/api/comandas/serie?dias=30").json()
        assert c["total"] == 5

    def test_la_serie_sigue_funcionando_sin_ninguna_comanda(self, cliente, almacen, descargas):
        from core.config import DIAS_FUTURO
        _sesion(cliente, USUARIO)
        almacen.filas.clear()
        r = cliente.get("/api/comandas/serie?dias=30")
        assert r.status_code == 200
        c = r.json()
        assert c["total"] == 0 and c["sin_asignar"] == 0
        assert c["rpx"] == [0] * (30 + DIAS_FUTURO)
