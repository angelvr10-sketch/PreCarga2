"""
core/comandas/edicion.py — Validacion de una comanda capturada a mano.

Es la unica puerta por la que entra una comanda que NO viene de un PDF. Todo lo
que `parser.py` garantiza por construccion (un folio con forma, numeros que son
numeros, un `tipo` dentro de dos valores) hay que comprobarlo aqui, porque el
cuerpo de la peticion lo escribe el navegador y puede traer cualquier cosa.

Este modulo es una funcion pura: no guarda nada y no habla con la base. Quien
guarda es `repository.py`; quien autoriza es `routers/api_comandas.py`.

── REGLAS, Y POR QUE CADA UNA ──────────────────────────────────────────────

- **folio**: al CREAR se pasa a mayusculas y se le quitan los espacios
  interiores ('oct 001' -> 'OCT001'). Los folios del reporte son tres letras y
  tres digitos (OCT001), pero se admite de 1 a 24 caracteres de [A-Z0-9 . _ / -]
  porque hay folios historicos con guion y barra. No se admiten espacios: el
  folio viaja en la URL del PDF individual y un espacio ahi es una fuente de
  404.

  Al MODIFICAR el folio se usa tal cual viene, SIN normalizar: es la llave con
  la que se busca la fila y hay filas historicas guardadas en minusculas por la
  app de Streamlit. Pasarlas a mayusculas aqui haria que el UPDATE no encontrara
  su propia fila y devolviera un 404 desconcertante para una comanda que se esta
  viendo en pantalla.

- **horario**: 'HH:MM'. Se normaliza '6:5' -> '06:05'. Es un campo que se imprime
  en el machote, asi que no puede quedar vacio.

- **compania / destino**: obligatorios, con los espacios colapsados (un PDF
  copiado a mano suele traer dobles espacios). Se conserva el uso de mayusculas
  y minusculas tal como se escribio: los datos reales vienen asi.

- **transporte**: lista cerrada (la misma de `parser.TRANSPORTES`). Se acepta
  'MARITIMO' sin acento y se guarda 'MARÍTIMO', que es como lo imprime el PDF.
  Vacio SI se admite: hay comandas que se capturan antes de saber el transporte,
  y el machote lo deja en blanco sin romperse.

- **tipo**: 'MORTERA' o 'VIANDA'. Por defecto VIANDA, que es lo que hace el
  parser cuando la columna no dice MORTERA.

- **pax**: NO se toma del cuerpo: es siempre `menu_1 + menu_2`, igual que
  `Comanda.total_pax` y que las estadisticas. El `pax` que llegue solo se valida
  (para rechazar un valor que no sea un entero) y se descarta: la API no puede
  guardar un total incoherente con los menus.

- **menu_1**: si no se manda, se copia del `pax` recibido. Eso mantiene la
  compatibilidad con el invariante del parser (en el reporte MENU 1 son las
  mismas personas que PAX) y con los clientes antiguos que solo mandaban `pax`.
  El formulario manda siempre los dos menus, asi que ahi el total es la suma
  real. Se admite un `menu_1` distinto del `pax` recibido (JUL026: pax 125,
  menu1 126): el total pasa a ser 126.

- **numeros**: se aceptan como texto ('12') porque la mayoria de los formularios
  HTML manda strings. Se rechazan negativos, decimales y valores absurdos.

Nada de esto recorta datos en silencio: cuando algo no cumple, se lanza
`ErrorComandaInvalida` con el nombre del campo y el motivo, y el router lo
convierte en un 400 con ese texto.
"""

from __future__ import annotations

import re

from core.comandas.parser import Comanda

# Limites. Son de cordura, no de negocio: existen para que un dedazo en la API
# no meta una fila de 2 MB en el JSONB.
MAX_TEXTO = 120
MAX_OBSERVACIONES = 500
MAX_PERSONAS = 10_000

# Un folio, sin espacios. Se admite punto, guion y barra por folios historicos.
RE_FOLIO = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{0,23}$")

# 'HH:MM' con una o dos cifras: se normaliza a dos ('6:5' -> '06:05').
RE_HORARIO = re.compile(r"^(\d{1,2}):(\d{1,2})$")

# La misma lista que `parser.TRANSPORTES`, pero como tupla para poder validar.
TRANSPORTES = ("AEREO", "GANGWAY", "MARÍTIMO", "VIUDA", "CANASTILLA")

# Lo que la gente escribe cuando no puede teclear la tilde.
ALIAS_TRANSPORTE = {"MARITIMO": "MARÍTIMO"}

TIPOS = ("MORTERA", "VIANDA")


class ErrorComandaInvalida(ValueError):
    """El cuerpo de la peticion no describe una comanda valida.

    `campo` viaja aparte del mensaje para que el frontend pueda resaltar el
    input que falla, si algun dia lo necesita. El router solo usa el texto.
    """

    def __init__(self, mensaje: str, campo: str = ""):
        super().__init__(mensaje)
        self.campo = campo


# ── Normalizadores ─────────────────────────────────────────────

def _texto(valor, campo: str, *, etiqueta: str | None = None,
           maximo: int = MAX_TEXTO, obligatorio: bool = False) -> str:
    """Texto de una linea, sin espacios de sobra en los extremos ni al centro.

    `campo` es el identificador (el que viaja en `ErrorComandaInvalida.campo`);
    `etiqueta` es como se llama en el mensaje, para no escribir "compania es
    obligatorio".
    """
    nombre = etiqueta or campo
    texto = " ".join(str(valor if valor is not None else "").split())
    if obligatorio and not texto:
        raise ErrorComandaInvalida(f"{nombre} es obligatorio", campo)
    if len(texto) > maximo:
        raise ErrorComandaInvalida(
            f"{nombre} no puede pasar de {maximo} caracteres", campo
        )
    return texto


def _entero(valor, campo: str, defecto: int = 0) -> int:
    """Entero >= 0. Acepta '12' (lo que manda un <input>) y rechaza decimales."""
    if valor is None or valor == "":
        return defecto
    if isinstance(valor, bool):
        # bool es subclase de int: `True` se colaria como 1 sin este caso.
        raise ErrorComandaInvalida(f"{campo} debe ser un numero entero", campo)
    try:
        numero = int(str(valor).strip())
    except (TypeError, ValueError):
        raise ErrorComandaInvalida(f"{campo} debe ser un numero entero", campo)
    if numero < 0 or numero > MAX_PERSONAS:
        raise ErrorComandaInvalida(
            f"{campo} debe estar entre 0 y {MAX_PERSONAS}", campo
        )
    return numero


def normalizar_folio(valor) -> str:
    """Folio en mayusculas y sin espacios. Es la llave de la fila al CREAR."""
    texto = str(valor if valor is not None else "").strip().upper()
    texto = "".join(texto.split())
    if not texto:
        raise ErrorComandaInvalida("El folio es obligatorio", "folio")
    if not RE_FOLIO.match(texto):
        raise ErrorComandaInvalida(
            f"Folio invalido: {texto!r}. Se admiten letras, numeros, punto, "
            "guion y barra (hasta 24 caracteres)",
            "folio",
        )
    return texto


def folio_existente(valor) -> str:
    """El folio de una comanda que YA esta en la base. No se normaliza.

    Ver la nota del encabezado: normalizar aqui romperia las filas historicas
    que la app vieja guardo en minusculas, porque el filtro de PostgREST es un
    `eq.` exacto. Solo se comprueba que no venga vacio ni absurdamente largo.
    """
    texto = str(valor if valor is not None else "").strip()
    if not texto:
        raise ErrorComandaInvalida("El folio es obligatorio", "folio")
    if len(texto) > 24:
        raise ErrorComandaInvalida(
            f"Folio invalido: {texto!r}. Como maximo 24 caracteres", "folio"
        )
    return texto


def normalizar_horario(valor) -> str:
    """'6:5' -> '06:05'. Vacio o fuera de rango es error."""
    texto = str(valor if valor is not None else "").strip()
    if not texto:
        raise ErrorComandaInvalida("El horario es obligatorio (HH:MM)", "horario")
    m = RE_HORARIO.match(texto)
    if not m:
        raise ErrorComandaInvalida(
            f"Horario invalido: {texto!r}. Se espera HH:MM", "horario"
        )
    horas, minutos = int(m.group(1)), int(m.group(2))
    if horas > 23 or minutos > 59:
        raise ErrorComandaInvalida(
            f"Horario fuera de rango: {texto!r} (00:00 a 23:59)", "horario"
        )
    return f"{horas:02d}:{minutos:02d}"


def normalizar_tipo(valor) -> str:
    texto = str(valor if valor is not None else "").strip().upper() or "VIANDA"
    if texto not in TIPOS:
        raise ErrorComandaInvalida(
            f"Tipo invalido: {texto!r}. Se espera MORTERA o VIANDA", "tipo"
        )
    return texto


def normalizar_transporte(valor) -> str:
    """Transporte de la lista cerrada. Vacio se admite; cualquier otra cosa no."""
    texto = " ".join(str(valor if valor is not None else "").split()).upper()
    texto = ALIAS_TRANSPORTE.get(texto, texto)
    if texto and texto not in TRANSPORTES:
        raise ErrorComandaInvalida(
            f"Transporte invalido: {texto!r}. Se espera uno de "
            f"{', '.join(TRANSPORTES)} (o dejarlo vacio)",
            "transporte",
        )
    return texto


# ── Punto de entrada ───────────────────────────────────────────

def comanda_desde_payload(payload: dict, folio: str | None = None) -> Comanda:
    """Convierte el JSON de la peticion en una `Comanda` validada.

    `folio` solo se pasa al MODIFICAR, donde el folio es fijo: es parte de la
    llave de la fila (folio, subido_por, fecha_registro) y cambiarlo seria mover
    el registro a otro sitio. Si el cuerpo trae otro folio, se rechaza en vez de
    ignorarlo: quien lo mando esperaba otra cosa y el silencio lo escondería.

    El `pax` del resultado NO es el del cuerpo: se deriva de `menu_1 + menu_2`
    (ver `Comanda.total_pax`). El `pax` recibido solo se valida y sirve de
    defecto para `menu_1` cuando este no viene.
    """
    if not isinstance(payload, dict):
        raise ErrorComandaInvalida("El cuerpo debe ser un objeto JSON")

    declarado = payload.get("comanda") or payload.get("folio")

    if folio is None:
        folio_limpio = normalizar_folio(declarado)
    else:
        folio_limpio = folio_existente(folio)
        if declarado and str(declarado).strip() != folio_limpio:
            raise ErrorComandaInvalida(
                "El folio no se puede cambiar: borra la comanda y vuelve a crearla",
                "comanda",
            )

    pax_recibido = _entero(payload.get("pax"), "PAX")
    menu_1 = _entero(
        payload.get("menu_1", payload.get("menu1")), "Menu 1", defecto=pax_recibido
    )
    menu_2 = _entero(payload.get("menu_2", payload.get("menu2")), "Menu 2")

    # PAX es derivado, no un dato que se capture: el total de personas es la
    # suma de los menus (misma regla que `Comanda.total_pax` y stats.py). Lo
    # recibido ya se valido arriba, pero no se usa.
    pax = menu_1 + menu_2

    if pax == 0:
        raise ErrorComandaInvalida(
            "La comanda no tiene personas: revisa el Menu 1 y el Menu 2", "pax"
        )
    # Cada menu ya se valido por separado; la suma tambien tiene que ser de
    # cordura, o dos valores validos de 10.000 dejan una fila absurda.
    if pax > MAX_PERSONAS:
        raise ErrorComandaInvalida(
            f"PAX debe estar entre 0 y {MAX_PERSONAS} (Menu 1 + Menu 2)", "pax"
        )

    return Comanda(
        comanda=folio_limpio,
        horario=normalizar_horario(payload.get("horario")),
        compania=_texto(payload.get("compania"), "compania",
                        etiqueta="La compañía", obligatorio=True),
        destino=_texto(payload.get("destino"), "destino",
                       etiqueta="El destino", obligatorio=True),
        pax=pax,
        transporte=normalizar_transporte(payload.get("transporte")),
        menu_1=menu_1,
        menu_2=menu_2,
        tipo=normalizar_tipo(payload.get("tipo")),
        observaciones=_texto(
            payload.get("observaciones"), "observaciones",
            etiqueta="Las observaciones", maximo=MAX_OBSERVACIONES,
        ),
    )
