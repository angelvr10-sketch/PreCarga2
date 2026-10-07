"""
routers/api_comandas.py — Endpoints JSON de comandas de alimentos.

Consume la sesion que ya tiene precarga2: entrar a `/comandas` es entrar a
`/dashboard`, con la misma cookie. No hay login propio.

Diez endpoints, agrupados en tres familias:

  Lectura    GET  /fechas                  fechas con datos del usuario
             GET  /                        comandas de una fecha
             GET  /estadisticas            las agregaciones del dashboard
  Escritura   POST /importar               sube un reporte PDF
  Reportes    GET  /reporte/{tipo}[/{folio}]   los cinco PDF

Tres reglas transversales que se aplican aqui y no en cada endpoint:

1. AUTORIZACION. `_usuario()` exige sesion y `_rol_autorizado()` exige el rol.
   El `usuario` NUNCA se toma del cuerpo de la peticion: sale de la cookie. Si
   un endpoint lo aceptara del body, el aislamiento por usuario se romperia.

2. CUOTA DE DESCARGAS. Como los PDF de precarga2, cada reporte de comandas
   descuenta una descarga (decision D3, 2026-10-06). Se comprueba con
   `puede_descargar` ANTES de generar: generar 30 paginas de reportlab para
   despues negarse a devolverlas es trabajo tirado. El contador se sube solo
   si el PDF se genero bien y la respuesta sale con status 200.

3. CPU EN HILOS. reportlab y pypdf son Python puro y bloquean. Con
   `--workers 2`, generar PDF en el event loop deja el servidor entero sin
   responder. Todo lo caro va en `run_in_threadpool`.
"""
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import Response, JSONResponse
from starlette.concurrency import run_in_threadpool

from core.auth import contar_descarga, get_current_user, puede_descargar
from core.comandas import (
    ErrorProcesandoPDF,
    calcular_estadisticas,
    hoy_iso,
    parse_pdf,
)
from core.comandas.fecha import fecha_largo_es, fecha_titulo_es
from core.comandas.pdf import pdf_comandas as _pdf_comandas
from core.comandas.pdf import (
    pdf_comanda,
    pdf_comandas_mortera,
    pdf_reporte_estadistico,
    pdf_vales,
)
from core.comandas.repository import (
    ErrorComandas,
    diagnostico,
    fechas_disponibles,
    listar,
    obtener,
    serie_diaria_barcos,
    upsert_masivo,
)

router = APIRouter(prefix="/api/comandas")

# Tamano maximo del reporte. Un PDF de 2 MB es enorme para una tabla de texto;
# un archivo mayor casi siempre es otra cosa (o un ataque).
MAX_BYTES_PDF = 20 * 1024 * 1024

# Roles que pueden generar los reportes de comandas en bloque. 'lector' se queda
# solo con el reporte estadistico y el PDF individual: la app de Streamlit era
# contradictoria en esto (daba el PDF individual al lector aunque el comentario
# de app.py:1731 decia que no), asi que aqui queda decidido y escrito.
ROLES_REPORTE_COMPLETO = ("admin", "usuario")
ROLES_LECTURA = ("admin", "usuario", "lector")

NOMBRE_TIPO = {
    "estadistico": "Reporte_Estadistico",
    "todas": "Todas_las_Comandas",
    "mortera": "Comandas_Mortera",
    "vales": "Vales_Alimentos",
}


# ── Autorizacion ───────────────────────────────────────────────

def _usuario(request: Request) -> dict:
    """Sesion valida o 401. El usuario sale siempre de la cookie."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user


def _rol_autorizado(user: dict, permitidos: tuple) -> dict:
    """El rol del usuario esta en la lista, o 403 con un mensaje util."""
    rol = (user.get("rol") or "").lower()
    if rol not in permitidos:
        raise HTTPException(
            status_code=403,
            detail=f"Tu rol ({rol or 'sin rol'}) no puede generar este reporte",
        )
    return user


# ── Utilidades ─────────────────────────────────────────────────

def _fecha(fecha: str | None) -> str:
    """Valida 'YYYY-MM-DD'. Fecha invalida es 400, no una excepcion del servidor.

    `datetime.strptime` acepta cosas que despues rompen al agrupar, asi que se
    round-trippea: se formatea lo parseado y se compara con lo recibido.
    """
    if not fecha:
        return hoy_iso()
    try:
        d = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Fecha invalida: {fecha!r}. Se espera YYYY-MM-DD"
        )
    return d.isoformat()


def _titulo_legible(titulo: str) -> str:
    """'REFORMA PEMEX' -> 'REFORMA_PEMEX' para el nombre del archivo.

    En la cabecera del Content-Disposition no pueden ir espacios ni acentos: el
    nombre se lo guarda el navegador y hay que evitar que lo normalice de
    forma distinta en cada uno.
    """
    return (titulo or "COMANDAS").replace(" ", "_").replace("Á", "A") \
        .replace("É", "E").replace("Í", "I").replace("Ó", "O") \
        .replace("Ú", "U").replace("Ü", "U")


def _pdf(datos: bytes, nombre: str) -> Response:
    return Response(
        content=datos,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre}"',
            # El PDF es de una operacion concreta y puede contener datos de
            # otras personas. El service worker ya no cachea /api/, pero el
            # navegador si cachea un attachment: sin esto se queda en disco.
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def _validar_pdf(subido: UploadFile) -> bytes:
    """Lee el archivo subido y lo valida antes de handing al parser."""
    if not (subido.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    datos = await subido.read()

    if not datos:
        raise HTTPException(status_code=400, detail="El archivo esta vacio")
    if len(datos) > MAX_BYTES_PDF:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo pesa {len(datos) / 1024 / 1024:.1f} MB y el maximo es 20 MB",
        )
    # Magic bytes: la extension la pone cualquiera, estos bytes no.
    if not datos.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="El archivo no es un PDF (no empieza por %PDF-)",
        )
    return datos


# ── Lectura ────────────────────────────────────────────────────

@router.get("/fechas")
async def fechas(request: Request):
    """Fechas en las que este usuario tiene comandas, de mas reciente a mas vieja.

    Se cachea 30 s y solo para esta persona: es la unica respuesta que cambia
    poco y la que la pantalla pide primero.
    """
    user = _usuario(request)
    try:
        lista = await run_in_threadpool(fechas_disponibles, user)
    except ErrorComandas as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return JSONResponse(
        {"fechas": lista, "hoy": hoy_iso()},
        headers={"Cache-Control": "private, max-age=30"},
    )


@router.get("/")
async def comandas_de_fecha(request: Request, fecha: str | None = None):
    """Las comandas del usuario en una fecha."""
    user = _usuario(request)
    f = _fecha(fecha)

    try:
        lista = await run_in_threadpool(listar, user, f)
    except ErrorComandas as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    titulo = "REFORMA PEMEX"
    if lista:
        try:
            titulo = await run_in_threadpool(_titulo_de_la_base, user, f)
        except ErrorComandas:
            # El titulo es cosmetico. Si no se puede deducir, se deja el
            # default en vez de fallar la carga de las comandas.
            pass

    return {
        "fecha": f,
        "comandas": [c.a_dict() for c in lista],
        "total": len(lista),
        "total_pax": sum(c.total_pax for c in lista),
        "titulo": titulo,
    }


def _titulo_de_la_base(usuario: dict, fecha_iso: str) -> str:
    """El titulo del proyecto, deducido del propio reporte guardado.

    El PDF de entrada lleva el proyecto en el pie (`CERRO DE LA PEZ` o
    `REFORMA PEMEX`). No hay columna para el, asi que se saca de las
    observaciones guardadas; si no esta, se usa el default.
    """
    from core.comandas.parser import RE_TITULO

    for c in listar(usuario, fecha_iso):
        for campo in (c.observaciones, c.compania, c.destino):
            m = RE_TITULO.search(campo)
            if m:
                return m.group(1).upper()
    return "REFORMA PEMEX"


@router.get("/estadisticas")
async def estadisticas(request: Request, fecha: str | None = None):
    """Las agregaciones del dashboard, ya calculadas en el servidor.

    El dashboard pide este endpoint y no las comandas sueltas para no tener que
    sumar en el navegador: el total de PAX es lo primero que mira la gente.
    """
    user = _usuario(request)
    f = _fecha(fecha)

    try:
        lista = await run_in_threadpool(listar, user, f)
    except ErrorComandas as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    s = calcular_estadisticas(lista)
    return {"fecha": f, **s.a_dict()}


@router.get("/serie")
async def serie(request: Request, dias: int = 30):
    """Comandas por dia, separadas por barco, en los ultimos `dias` dias.

    Es la unica lectura de este router que NO es por usuario: alimenta una
    tarjeta y una grafica del DASHBOARD, donde todo lo demas ya es global. Solo
    devuelve conteos, nunca el contenido de una comanda. La razon esta escrita
    en `repository.serie_diaria_barcos`, que es donde esta el riesgo real.

    `dias` se recorta a 1..365 en `serie.ventana`, igual que las graficas de
    altas/bajas del dashboard, para que las dos compartan el selector de periodo.
    """
    _rol_autorizado(_usuario(request), ROLES_LECTURA)

    try:
        return await run_in_threadpool(serie_diaria_barcos, dias)
    except ErrorComandas as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Escritura ──────────────────────────────────────────────────

@router.post("/importar")
async def importar(request: Request, file: UploadFile = File(...)):
    """Sube un reporte PDF y guarda sus comandas.

    Es idempotente: volver a subir el mismo reporte actualiza las comandas de
    esos folios en vez de duplicarlas. No borra comandas que ya estaban y que
    este reporte no menciona: el reporte manda lo que trae, no lo que deja de
    traer.
    """
    user = _usuario(request)
    datos = await _validar_pdf(file)

    try:
        r = await run_in_threadpool(parse_pdf, datos)
    except ErrorProcesandoPDF as exc:
        # 422: el archivo es un PDF valido pero no es un reporte de comandas.
        # Es distinto de un 400 (archivo roto) y de un 500 (nosotros).
        return JSONResponse(
            status_code=422,
            content={"ok": False, "mensaje": str(exc)},
        )

    try:
        guardado = await run_in_threadpool(
            upsert_masivo, user, r.fecha_iso, r.comandas
        )
    except ErrorComandas as exc:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "mensaje": str(exc)},
        )

    return {
        "ok": True,
        "fecha": r.fecha_iso,
        "fecha_texto": r.fecha_texto,
        "titulo": r.titulo,
        "guardadas": guardado["guardadas"],
        "folios": guardado["folios"],
        "total": len(r.comandas),
        "total_pax": r.total_pax,
        "morteras": sum(1 for c in r.comandas if c.tipo == "MORTERA"),
        "advertencias": r.advertencias,
        # Para el toast del frontend: "N comandas del 13/05/2026".
        "mensaje": (
            f"{len(r.comandas)} comandas guardadas "
            f"({r.total_pax} PAX) del {fecha_titulo_es(_a_fecha(r.fecha_iso))}"
        ),
    }


def _a_fecha(fecha_iso: str) -> date:
    return datetime.strptime(fecha_iso, "%Y-%m-%d").date()


# ── Reportes ───────────────────────────────────────────────────

@router.get("/reporte/estadistico")
async def reporte_estadistico(request: Request, fecha: str | None = None):
    """Reporte de una hoja: donut por destino, barras por transporte, companias."""
    return await _generar_pdf(request, fecha, "estadistico")


@router.get("/reporte/todas")
async def reporte_todas(request: Request, fecha: str | None = None):
    """Todas las comandas, una por pagina."""
    return await _generar_pdf(request, fecha, "todas")


@router.get("/reporte/mortera")
async def reporte_mortera(request: Request, fecha: str | None = None):
    """Todas las comandas, con las de tipo MORTERA ampliadas a 6 firmas."""
    return await _generar_pdf(request, fecha, "mortera")


@router.get("/reporte/vales")
async def reporte_vales(request: Request, fecha: str | None = None):
    """Vales de alimentos, 10 por hoja."""
    return await _generar_pdf(request, fecha, "vales")


@router.get("/reporte/comanda/{folio}")
async def reporte_comanda(request: Request, folio: str, fecha: str | None = None):
    """Una sola comanda en una pagina."""
    user = _usuario(request)
    _rol_autorizado(user, ROLES_LECTURA)
    f = _fecha(fecha)

    comanda = await run_in_threadpool(obtener, user, f, folio)
    if comanda is None:
        # 404 y no 403: no se le dice a un usuario si el folio existe en la base
        # de otro usuario.
        raise HTTPException(status_code=404, detail=f"No hay comanda {folio} en esa fecha")

    await _cobrar_descarga(user, f"Necesitas una descarga para ver {folio}")

    fecha_texto, titulo = await run_in_threadpool(_contexto_de_fecha, user, f)
    datos = await run_in_threadpool(pdf_comanda, comanda, fecha_texto, titulo)
    return _pdf(datos, f"Comanda_{folio}.pdf")


async def _generar_pdf(request: Request, fecha: str | None, tipo: str):
    """El camino comun de los cuatro reportes en bloque."""
    user = _usuario(request)
    _rol_autorizado(user, ROLES_REPORTE_COMPLETO)
    f = _fecha(fecha)

    lista = await run_in_threadpool(listar, user, f)
    if not lista:
        # 404 con mensaje util: el boton se deshabilita cuando no hay datos, asi
        # que llegar aqui es raro, y decir "no hay nada" ayuda mas que un PDF
        # vacio.
        raise HTTPException(
            status_code=404,
            detail=f"No hay comandas del {f} para generar el reporte",
        )

    fecha_texto, titulo = await run_in_threadpool(_contexto_de_fecha, user, f)

    def _generar():
        if tipo == "estadistico":
            return pdf_reporte_estadistico(lista, fecha_texto, titulo)
        if tipo == "todas":
            return _pdf_comandas(lista, fecha_texto, titulo)
        if tipo == "mortera":
            return pdf_comandas_mortera(lista, fecha_texto, titulo)
        if tipo == "vales":
            return pdf_vales(lista, fecha_texto)
        raise HTTPException(status_code=500, detail=f"Tipo de reporte desconocido: {tipo}")

    # La cuota se comprueba ANTES de generar: son 30 paginas de reportlab que
    # se harian para nada si despues va a decir que no.
    await _cobrar_descarga(user, "Te quedaste sin descargas para generar el reporte")

    datos = await run_in_threadpool(_generar)
    nombre = f"{NOMBRE_TIPO[tipo]}_{_titulo_legible(titulo)}.pdf"
    return _pdf(datos, nombre)


def _contexto_de_fecha(usuario: dict, fecha_iso: str) -> tuple[str, str]:
    """(fecha_texto, titulo) para dibujar en el machote.

    La fecha se reconstruye desde la fecha ISO de la base, no desde el texto
    que traia el PDF: asi el PDF sale igual aunque se vuelva a generar otro dia.
    """
    f = datetime.strptime(fecha_iso, "%Y-%m-%d").date()
    return fecha_largo_es(f), _titulo_de_la_base(usuario, fecha_iso)


async def _cobrar_descarga(user: dict, mensaje_si_no: str) -> None:
    """Comprueba la cuota y, si hay, descuenta una descarga.

    Decision D3 (2026-10-06): los PDF de comandas cuentan para
    `descargas_usadas`, igual que los de precarga2.

    Nota sobre `contar_descarga`: lee el contador y luego lo incrementa con dos
    peticiones separadas, asi que dos descargas simultaneas pueden perder una
    cuenta. No se arregla aqui a proposito: `core/auth.py` es compartido con
    los demas routers y cambiarlo afecta a toda la app. Se anota para que no se
    lea esto como si el contador fuera atomico.
    """
    permitido, razon = puede_descargar(user)
    if not permitido:
        raise HTTPException(status_code=402, detail=mensaje_si_no or razon)
    contar_descarga(user["id"])


# ── Soporte ────────────────────────────────────────────────────

@router.get("/diagnostico")
async def diagnostico_de_datos(request: Request):
    """Conteos de la base. Solo admin: cuenta datos de todos los usuarios."""
    user = _usuario(request)
    _rol_autorizado(user, ("admin",))

    info = await run_in_threadpool(diagnostico, user)
    return info
