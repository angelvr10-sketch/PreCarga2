"""
core/comandas/parser.py — Lectura de los PDF de comandas.

Port literal de `ComandaApp.parse_pdf` de la app de Streamlit (app.py:419-555),
sin la dependencia de Streamlit y sin escribir en la base de datos: este modulo
SOLO lee texto y devuelve datos. Quien guarda es `repository.py`.

Regla que manda: los regex y las limpiezas son los de siempre. Este parser es el
corazon del sistema y ya funciona con los PDF reales de la plataforma; tocarlo
sin un PDF de prueba al lado es la forma mas rapida de romper la operacion.

Los unicos cambios respecto al original son:
  1. `st.error(...)` se reemplaza por excepciones tipadas.
  2. El merge con las comandas ya guardadas (que era estado de sesion) desaparece:
     la base de datos resuelve eso con `upsert`.
  3. La normalizacion de fecha pasa por `fecha.py`, sin `strftime("%B")`.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime

from pypdf import PdfReader

from core.comandas.fecha import resolver_fecha_operacion, texto_fecha_del_pdf


class ErrorProcesandoPDF(ValueError):
    """El PDF no se pudo leer o no traia comandas."""


# ── Vocabulario de destinos ────────────────────────────────────
# Plataformas,Producto y proyectos donde se entrega. Es una lista cerrada a
# proposito: el regex la usa como delimitador, asi que cualquier palabra que
# quede fuera se pierde. Agregar un destino nuevo es agregar su alternativa
# aqui.
DESTINO_PATTERN = (
    r'(?:PLATAFORMA\s+CAMPECHE|ORGULLO\s+PETROLERO|'
    r'WEST\s+COURAGEOUS|WEST\s+DEFENDER|WEST\s+INTREPID|'
    r'GRAND\s+CANYON|ARBOL\s+GRANDE|GARZPROM\s+II|'
    r'CAYO\s+ARCAS|TARATUNICH|CB\s+LITORAL|PAPALOAPAN|'
    r'BLUE\s+GIANT|BLUE\s+PIONEER|BARCO\s+LA\s+BAMBA|'
    r'CREST-CENTURION|ENLACE\s+LITORAL|LITORAL\s+TABASCO|'
    r'LITORAL\s+A|CIA\s+C/G|OCH-TAN-A|'
    r'REFORMA\s+PEMEX|CERRO\s+DE\s+LA\s+PEZ|'
    r'ABKATUN|AKAL|ALUX|AYATSIL|BALAM-T[AE]|BATAB|BOLONTIKU|'
    r'CAAN|CHEEK|CHE|CHIHUAHUA|CHUC|CHUHUK|COESL|COVADONGA|'
    r'EKTAL|EKU|ELT|ESAH|ETKAL|EK|GABINETE|GERSEMI|'
    r'HAYABIL|HERCULES|HOK|HOMOL|IXTAL|'
    r'KAB|KAX|KIX|KU|KUIL|KUKULKAN|LATINA|LTH|'
    r'MALOOB|MANIK|MAY|MULACH|NEPTUNO|NOHOCH|OCH|ONEL|'
    r'PB-LIT|POL|PROTEUS|REBOMBEO|'
    r'SINAN|TEHUANA|TSIMIN|T-SIMIN|TUMUT|TUXPANAPA|ITTA-A|SIHIL-A|'
    r'UECH|XANAB|XIKIN|XUB|XUX|YAXCHE|YKN|YUM|ZAAP|ZACATECAS)'
    r'[\w\s\-/\[\]]*?'
)

TRANSPORTES = r'AEREO|GANGWAY|MARÍTIMO|VIUDA|CANASTILLA'

# ── Titulo del proyecto ────────────────────────────────────────
RE_TITULO = re.compile(r'(REFORMA\s+PEMEX|CERRO\s+DE\s+LA\s+PEZ)', re.IGNORECASE)

TITULO_POR_DEFECTO = "ALIMENTOS AL AREA"
TITULO_ALTERNATIVO = "REFORMA PEMEX"

# ── Modelo ─────────────────────────────────────────────────────

@dataclass
class Comanda:
    """Una comanda de alimentos. Mismo esquema que el JSON guardado en Supabase."""

    comanda:      str   # folio, ej. 'ABC123'
    horario:      str   # '08:30'
    compania:     str
    destino:      str
    pax:          int
    transporte:   str
    menu_1:       int
    menu_2:       int
    tipo:         str   # 'MORTERA' | 'VIANDA'
    observaciones: str

    @property
    def total_pax(self) -> int:
        return self.menu_1 + self.menu_2

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResultadoParse:
    """Lo que devuelve `parse_pdf`. El router lo pasa a JSON."""

    comandas:      list[Comanda]
    fecha_iso:     str                    # 'YYYY-MM-DD' — llave de agrupacion en la BD
    fecha_texto:   str                    # 'MARTES, 13 DE MAYO DE 2026' — para el machote
    titulo:        str
    advertencias:  list[str] = field(default_factory=list)

    @property
    def total_pax(self) -> int:
        return sum(c.total_pax for c in self.comandas)


# ── Regex compilados ───────────────────────────────────────────
# Se compilan una vez al importar el modulo. El original compilaba el patron de
# observaciones en cada llamada a parse_pdf.

RE_OBSERVACIONES = re.compile(
    r'(?P<comanda>[A-Z]{3}\d+)\s+\d{2}:\d{2}\s+'
    r'(?:[\w\.\-]+(?:\s+[\w\.\-]+){0,4}?)\s+'
    + DESTINO_PATTERN +
    r'\s+\d{1,3}\s+(?:AEREO|GANGWAY|MARÍTIMO|VIUDA|CANASTILLA)\s+'
    r'\d{1,3}\s+\d{1,3}'
)

RE_COMANDA = re.compile(
    r'(?P<comanda>[A-Z]{3}\d+)\s+'
    r'(?P<horario>\d{2}:\d{2})\s+'
    r'(?P<compania>(?:[\w\.\-]+(?:\s+[\w\.\-]+){0,4}?))\s+'
    rf'(?P<destino>{DESTINO_PATTERN})\s+'
    r'(?P<pax>\d{1,3})\s+'
    rf'(?P<transporte>{TRANSPORTES})\s+'
    r'(?P<m1>\d{1,3})\s+'
    r'(?P<m2>\d{1,3})'
)

# Candidatos a folio para el aviso de "no se interpretaron".
#
# NO puede ser `[A-Z]{3}\d+` a secas: en la columna de observaciones aparece
# 'MENU1-VIANDA', y eso se leeria como un folio llamado 'ENU1'. El aviso
# entonces reportaba una comanda perdida que no existe.
#
# Un folio real siempre va seguido de su hora, asi que se exige la forma
# completa: tres letras, dos a seis digitos, un espacio y HH:MM.
_RE_FOLIO_CANDATOS = re.compile(r'(?<![\w-])([A-Z]{3}\d{2,6})\s+\d{2}:\d{2}(?![\d:])')


# ── Paso 1: texto del PDF ──────────────────────────────────────

def texto_del_pdf(file_bytes: bytes) -> str:
    """Saca el texto de las paginas y lo aplana a una sola linea logica.

    El reporte viene en una tabla y `extract_text` mete saltos de linea en
    lugares que no siguen las filas. Estas dos sustituciones son las que
    hacían que los regex vieran una comanda por linea.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        crudo = ""
        for pagina in reader.pages:
            crudo += (pagina.extract_text() or "") + "\n"
    except Exception as exc:
        raise ErrorProcesandoPDF(f"No se pudo leer el PDF: {exc}") from exc

    if not crudo.strip():
        raise ErrorProcesandoPDF("El PDF no contiene texto extraíble "
                                 "(¿es un PDF escaneado por imagen?)")

    texto = re.sub(r'\n(?![A-Z]{3}\d+\s)', ' ', crudo)
    return re.sub(r'\s{2,}', ' ', texto)


# ── Paso 2: campos de cabecera ─────────────────────────────────

def titulo_del_pdf(texto: str) -> str:
    """'REFORMA PEMEX' / 'CERRO DE LA PEZ' / 'ALIMENTOS AL AREA'."""
    m = RE_TITULO.search(texto)
    return m.group(1).upper() if m else TITULO_POR_DEFECTO


# ── Paso 3: observaciones ──────────────────────────────────────
# Las observaciones van DESPUES de los numeros de la comanda y no tienen
# delimitador fijo: se toma todo lo que hay entre esta comanda y la siguiente,
# y se descarta lo que claramente no es texto nuestro (encabezados, dias de la
# semana, la fila de numeros que ya se leyo).

_RE_LIMPIAR_OBSERVACIONES = re.compile(
    r'NO\.\s*COM\..*?OBSERVACIONES|CONTRATO\s+No\..*|'
    r'CERRO\s+DE\s+LA\s+PEZ|REFORMA\s+PEMEX|'
    r'COMANDA\s+DE\s+ALIMENTOS|'
    r'(domingo|lunes|martes|miércoles|jueves|viernes|sábado)'
    r',?\s*\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',
    re.IGNORECASE
)


def observaciones_por_folio(texto: str) -> dict[str, str]:
    """Devuelve {folio: observaciones} para todas las comandas del reporte."""
    coincidencias = list(RE_OBSERVACIONES.finditer(texto))
    resultado: dict[str, str] = {}

    for indice, m in enumerate(coincidencias):
        folio = m.group('comanda')
        # El texto de esta comanda va desde el final de SU coincidencia hasta
        # donde empieza la siguiente: ahi esta el borde del bloque.
        inicio = m.end()
        fin = (
            coincidencias[indice + 1].start()
            if indice + 1 < len(coincidencias)
            else len(texto)
        )
        bruto = texto[inicio:fin].strip()

        # La fila 'M1 M2 FOLIO' que segue: sus numeros no son observaciones.
        bruto = re.sub(r'\b\d{1,3}\s+\d{1,3}\s+\d{2}\b', '', bruto)
        bruto = _RE_LIMPIAR_OBSERVACIONES.sub('', bruto)
        bruto = re.sub(r'^MEN[ÚU]?\s*\d\s*[-–]?\s*', '', bruto, flags=re.IGNORECASE)
        bruto = re.sub(r'^\d{1,3}\s*', '', bruto)
        bruto = re.sub(r'\s+', ' ', bruto).strip().strip(',').strip()

        # Si dos bloques del mismo folio se pisan, gana el mas largo: suele
        # ser el que si traia contenido y el otro solo ruido.
        if len(bruto) > len(resultado.get(folio, '')):
            resultado[folio] = bruto

    return resultado


# ── Paso 4: comandas ───────────────────────────────────────────

def comandas_del_texto(texto: str) -> list[Comanda]:
    """Extrae la lista de comandas del texto plano del reporte."""
    observaciones = observaciones_por_folio(texto)

    # Un folio repetido en el mismo PDF se conserva una sola vez, en su ultima
    # aparicion: el PDF mas reciente manda.
    por_folio: dict[str, Comanda] = {}

    for m in RE_COMANDA.finditer(texto):
        folio = m.group('comanda')
        obs = observaciones.get(folio, '')
        pax = int(m.group('pax'))

        por_folio[folio] = Comanda(
            comanda=folio,
            horario=m.group('horario'),
            compania=' '.join(m.group('compania').split()),
            destino=' '.join(m.group('destino').split()),
            pax=pax,
            transporte=m.group('transporte'),
            # El original prioriza No. Pax sobre Menu 1: el PDF trae las dos
            # columnas y el conteo de personas manda.
            menu_1=pax,
            menu_2=int(m.group('m2')),
            tipo='MORTERA' if 'MORTERA' in obs.upper() else 'VIANDA',
            observaciones=obs,
        )

    return list(por_folio.values())


# ── Punto de entrada ───────────────────────────────────────────

def parse_pdf(file_bytes: bytes) -> ResultadoParse:
    """Parsea un PDF de comandas completo.

    Lanza `ErrorProcesandoPDF` si el archivo no se puede leer o si no sale
    ninguna comanda. No escribe nada en la base de datos.
    """
    texto = texto_del_pdf(file_bytes)

    fecha_iso, fecha_texto = resolver_fecha_operacion(texto)
    titulo = titulo_del_pdf(texto)
    comandas = comandas_del_texto(texto)

    if not comandas:
        raise ErrorProcesandoPDF(
            "No se encontraron comandas en el PDF. Puede ser que el reporte "
            "venga en otro formato, o que los destinos no esten en la lista "
            "reconocida."
        )

    advertencias = _advertencias(texto, comandas)

    return ResultadoParse(
        comandas=comandas,
        fecha_iso=fecha_iso,
        fecha_texto=fecha_texto,
        titulo=titulo,
        advertencias=advertencias,
    )


def _advertencias(texto: str, comandas: list[Comanda]) -> list[str]:
    """Señales de que algo pudo quedar fuera, sin Cancelar la importacion.

    Es una red de seguridad: el parser nunca falla por esto, solo avisa. Si el
    reporte tiene folios que no entraron, el usuario ve el conteo y puede
    reportarlo, en vez de creer que se guardo todo.
    """
    avisos: list[str] = []

    # Folios citados en el PDF que no llegaron a ser una comanda completa.
    folios_en_texto = set(_RE_FOLIO_CANDATOS.findall(texto))
    folios_parseados = {c.comanda for c in comandas}
    perdidos = folios_en_texto - folios_parseados
    if perdidos:
        perdidos_ordenados = sorted(perdidos)[:10]
        sufijo = f" (+{len(perdidos) - 10} mas)" if len(perdidos) > 10 else ""
        avisos.append(
            f"{len(perdidos)} folio(s) del PDF no se interpretaron: "
            f"{', '.join(perdidos_ordenados)}{sufijo}"
        )

    if not texto_fecha_del_pdf(texto):
        avisos.append(
            "El PDF no trae fecha en el encabezado; se guardo con la fecha de hoy."
        )

    return avisos
