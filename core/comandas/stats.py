"""
core/comandas/stats.py — Agregaciones del dashboard y del reporte estadistico.

Port literal de `ComandaApp.calcular_estadisticas` (app.py:557-588). Devuelve el
mismo diccionario con las mismas claves para que el frontend nuevo y el reporte
PDF consuman exactamente lo mismo.

La separacion entre `por_destino` y `por_destino_grafico` no es redundancia: la
grafica acorta el nombre para que quepa en la leyenda del donut, mientras que la
tabla muestra el nombre completo. Se conserva tal cual.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.comandas.parser import Comanda

# Abreviatura de transporte para la leyenda de la grafica.
ABREV_TRANSPORTE = {"GANGWAY": "G", "MARÍTIMO": "M"}


@dataclass
class Estadisticas:
    """Mismo contenido que devolvia el diccionario original."""

    total_comandas: int = 0
    total_alimentos: int = 0
    total_menu1: int = 0
    total_menu2: int = 0
    total_mortera: int = 0

    por_destino: dict[str, int] = field(default_factory=dict)
    por_destino_grafico: dict[str, int] = field(default_factory=dict)
    por_compania: dict[str, int] = field(default_factory=dict)
    por_transporte: dict[str, int] = field(default_factory=dict)

    @property
    def total_viandas(self) -> int:
        return self.total_alimentos - self.total_mortera

    def a_dict(self) -> dict:
        """Serializable para la respuesta JSON de la API."""
        return {
            "total_comandas": self.total_comandas,
            "total_alimentos": self.total_alimentos,
            "total_menu1": self.total_menu1,
            "total_menu2": self.total_menu2,
            "total_mortera": self.total_mortera,
            "total_viandas": self.total_viandas,
            "por_destino": self.por_destino,
            "por_destino_grafico": self.por_destino_grafico,
            "por_compania": self.por_compania,
            "por_transporte": self.por_transporte,
        }


def calcular_estadisticas(comandas: list[Comanda]) -> Estadisticas:
    """Suma PAX por destino, compania y transporte.

    Acepta objetos `Comanda` o diccionarios con las mismas claves, para poder
    reutilizarla tanto con lo que devuelve el parser como con lo que viene de la
    base de datos.
    """
    s = Estadisticas()

    if not comandas:
        return s

    s.total_comandas = len(comandas)
    s.total_menu1 = _suma(comandas, 'menu_1')
    s.total_menu2 = _suma(comandas, 'menu_2')
    s.total_alimentos = s.total_menu1 + s.total_menu2
    s.total_mortera = _suma(
        [c for c in comandas if _tipo(c) == 'MORTERA'],
        'menu_1', 'menu_2',
    )

    for c in comandas:
        pax = _total_de(c)
        transporte = _texto(c, 'transporte')
        destino = _texto(c, 'destino')

        # 'AEREO' se agrupa solo (los aereos no van a un destino concreto);
        # canastilla conserva el destino porque va en barco; el resto lleva el
        # modo de entrega completo o abreviado segun la vista.
        if transporte == "AEREO":
            clave_tabla = "AÉREOS"
            clave_grafica = "AÉREOS"
        elif transporte == "CANASTILLA":
            clave_tabla = f"{destino.upper()} (CANASTILLA)"
            clave_grafica = f"{destino.upper()} (C)"
        else:
            clave_tabla = f"{destino.upper()} ({transporte})"
            clave_grafica = f"{destino.upper()} ({ABREV_TRANSPORTE.get(transporte, transporte)})"

        _sumar(s.por_destino, clave_tabla, pax)
        _sumar(s.por_destino_grafico, clave_grafica, pax)
        _sumar(s.por_compania, _texto(c, 'compania'), pax)
        _sumar(s.por_transporte, transporte, pax)

    return s


# ── Lectura tolerante de comandas ──────────────────────────────
# El parser entrega dataclasses, la base de datos entrega diccionarios con la
# columna `datos` envuelta. Estas cuatro funciones evitan repetir el
# `isinstance` en cada linea.

def _texto(comanda, clave: str) -> str:
    valor = getattr(comanda, clave, None) if not isinstance(comanda, dict) \
        else comanda.get(clave)
    return str(valor) if valor is not None else ''


def _numero(comanda, clave: str) -> int:
    valor = getattr(comanda, clave, None) if not isinstance(comanda, dict) \
        else comanda.get(clave)
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _tipo(comanda) -> str:
    return _texto(comanda, 'tipo').upper()


def _total_de(comanda) -> int:
    return _numero(comanda, 'menu_1') + _numero(comanda, 'menu_2')


def _suma(comandas, *claves: str) -> int:
    return sum(_numero(c, clave) for c in comandas for clave in claves)


def _sumar(diccionario: dict[str, int], clave: str, cantidad: int) -> None:
    # `destino` vacio daria una clave "" en la leyenda del grafico.
    if not clave:
        clave = "(SIN DESTINO)"
    diccionario[clave] = diccionario.get(clave, 0) + cantidad
