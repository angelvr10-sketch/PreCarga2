"""
core/comandas/serie.py — Serie diaria de comandas por barco.

De donde sale el "barco", que NO esta en los datos:

    La tabla `comandas` no tiene ninguna columna de barco. Se comprobo sobre las
    5,545 filas: 92 destinos distintos (POL-A, ABKATUN A, KU-A, ZAAP-C...) y CERO
    filas que mencionen RPX o CPZ. El `destino` de una comanda es una plataforma
    o proyecto, que es otra cosa distinta a un barco.

    En el dashboard de precarga2 el barco sale de `solicitudes.destinohosp`, que
    si usa RPX/CPZ, pero esa tabla no tiene comandas. Los dos vocabularios no se
    cruzan.

    Asi que por ahora el barco se deduce de QUIEN subio la comanda, con este mapa.
    Es un marcador, no un dato: si manana la division de comandas por barco cambia,
    o un cuarto usuario sube un reporte, este diccionario hay que actualizarlo, y
    por eso vive aqui, en un solo sitio y con su propio archivo de pruebas.

Lo que NO hace, a proposito: tirar en silencio las comandas de un usuario que no
esta en el mapa. Van a `sin_asignar`, y el frontend avisa. Un total de comandas
que no cuadra con la suma de las series es el peor fallo posible en una grafica
de control, porque parece un dato y no lo es.

Funciones puras: reciben filas y devuelven diccionarios. No tocan la base; quien
lo hace es `repository.serie_diaria_barcos`.
"""
from __future__ import annotations

from datetime import date, timedelta

# Los dos barcos del dashboard. El orden fija el de las series y el de la leyenda.
BARCOS = ("RPX", "CPZ")

# Usuario (en minusculas, como `clave_de_usuario` los deja) -> barco.
#
# `comandas.subido_por` guarda SIEMPRE el username en minusculas, pero el nombre
# en `usuarios` viene con mayusculas ('PabloDG', 'LuisE'), asi que la clave va
# normalizada y la comparacion tambien. Con `pablodg` como clave, `PabloDG` y
# `pablodg` caen en el mismo barco.
BARCO_POR_USUARIO: dict[str, str] = {
    "erika": "RPX",
    "pablodg": "RPX",
    "luise": "CPZ",
}

# Ventana maxima en dias, igual que `_agregar_ultimos_dias` de routers/api_data.py.
# Las dos graficas comparten el selector de periodo, asi que tienen que aceptar lo
# mismo o el dashboard mixes periodos.
DIAS_MAX = 365


def clasificar_barco(username: str | None) -> str | None:
    """El barco de un usuario, o None si no esta en el mapa.

    No lanza ni adivina: un usuario desconocido NO es RPX por defecto, porque
    atribuir sus comandas al barco equivocado en silencio es peor que reportar
    que falta la asignacion.
    """
    return BARCO_POR_USUARIO.get((username or "").strip().lower())


def ventana(dias: int, hoy: date | None = None) -> list[str]:
    """Los `dias` dias que terminan HOY, en orden cronologico (mas viejo -> hoy).

    Igual que `_agregar_ultimos_dias`: `range(dias - 1, -1, -1)`. Devuelve SIEMPRE
    `dias` elementos, con ceros donde no hay datos, porque el eje X del grafico
    tiene que alinearse con las dos series.
    """
    dias = max(1, min(int(dias), DIAS_MAX))
    hoy = hoy or date.today()
    return [(hoy - timedelta(days=i)).isoformat() for i in range(dias - 1, -1, -1)]


def serie_diaria(
    filas: list[dict],
    dias: int,
    hoy: date | None = None,
) -> dict:
    """Cuenta las comandas de cada dia, separadas por barco.

    `filas` son filas de `comandas` o cualquier dict con `fecha_registro` y
    `subido_por`. Se leen con `[]` y no con `.get()` obligatorio, y se ignoran las
    filas sin fecha o con fecha fuera de la ventana, en vez de reventar: un dato
    sucio no debe tumbar la grafica del dashboard.

    Devuelve:

        dias         las fechas de la ventana, en orden
        rpx          comandas por dia de RPX
        cpz          comandas por dia de CPZ
        sin_asignar  TOTAL (no diario) de comandas de usuarios fuera del mapa
        total        total de comandas de la ventana, contado sin filtro de barco

    `sin_asignar` es un total de la ventana, no una serie diaria, a proposito: el
    frontend solo lo usa para avisar "hay N comandas sin barco asignado".
    """
    fechas = ventana(dias, hoy)
    conteo = {f: {b: 0 for b in BARCOS} for f in fechas}

    sin_asignar = 0
    total = 0

    for fila in filas:
        fecha = (fila.get("fecha_registro") or "").strip()[:10]
        if fecha not in conteo:
            continue
        total += 1
        barco = clasificar_barco(fila.get("subido_por"))
        if barco is None:
            sin_asignar += 1
            continue
        conteo[fecha][barco] += 1

    return {
        "dias": fechas,
        "rpx": [conteo[f]["RPX"] for f in fechas],
        "cpz": [conteo[f]["CPZ"] for f in fechas],
        "sin_asignar": sin_asignar,
        "total": total,
    }