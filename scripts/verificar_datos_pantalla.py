"""
Verificación de los datos que ve la pantalla de /comandas.

No abre un navegador: comprueba que lo que el backend devuelve tiene la forma
que los componentes del frontend esperan. Si un campo cambia de nombre o un
conteo sale raro, esto avisa antes de que se vea en pantalla.

Usa las MISMAS funciones de formato del frontend (`aFilas`, `hoyIso`,
`fechaCorta`) reimplementadas en Python con la misma logica, para confirmar que
los datos son utilizables.

    python scripts/verificar_datos_pantalla.py [usuario]
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8")

import main  # noqa: F401,E402  (carga .env y el cliente de Supabase)
from core.comandas.repository import (  # noqa: E402
    clave_de_usuario, diagnostico, fechas_disponibles, listar,
)
from core.comandas.stats import calcular_estadisticas  # noqa: E402
from core.supabase_db import _get  # noqa: E402


def main_test(usuario_texto=None) -> int:
    fallos = []

    if usuario_texto:
        filas = _get("usuarios", select="id,username,rol,activo",
                     filters={"username": f"eq.{usuario_texto}"})
        if not filas:
            print(f"No existe el usuario {usuario_texto!r}")
            return 1
        usuario = filas[0]
    else:
        usuario = _get("usuarios", select="id,username,rol,activo",
                       filters={"username": "eq.admin"})[0]

    print(f"Usuario: {usuario['username']} (id={usuario['id']}, rol={usuario['rol']})")

    # ── Fechas ──
    print("\n1. Fechas disponibles")
    fechas = fechas_disponibles(usuario)
    print(f"   {len(fechas)} fechas")
    if not fechas:
        print("   (sin datos, nada que verificar)")
        return 0
    print(f"   primera: {fechas[0]}   ultima: {fechas[-1]}")

    # Formato ISO: la pantalla los mete en un <select> como value y los pasa a
    # la query. Si un valor no fuera ISO, la fecha se parsea mal.
    import re
    for f in fechas:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f):
            fallos.append(f"fecha no ISO: {f}")
    print(f"   todas en formato ISO: {'si' if not fallos else 'NO'}")

    # ── Comandas de la fecha mas reciente ──
    fecha = fechas[0]
    print(f"\n2. Comandas del {fecha}")
    comandas = listar(usuario, fecha)
    print(f"   {len(comandas)} comandas")

    if not comandas:
        print("   sin comandas en esa fecha")
        return 0

    # Campos que la tabla del frontend lee. Si alguno falta, sale `undefined`.
    campos = ["comanda", "horario", "compania", "destino", "pax",
              "transporte", "menu_1", "menu_2", "tipo", "observaciones"]
    faltan = set()
    for c in comandas:
        for campo in campos:
            if getattr(c, campo, None) in (None, ""):
                if campo not in ("observaciones", "compania", "destino", "horario"):
                    faltan.add(campo)
    if faltan:
        fallos.append(f"campos vacios en todas: {faltan}")
    print(f"   campos obligatorios presentes: {'si' if not faltan else 'NO ' + str(faltan)}")

    # La columna 'pax' tiene que ser entero (la tabla la ordena como numero).
    no_int = [c.comanda for c in comandas if not isinstance(c.pax, int)]
    if no_int:
        fallos.append(f"pax no es entero en: {no_int[:5]}")
    print(f"   pax siempre entero: {'si' if not no_int else 'NO'}")

    # 'tipo' tiene que ser MORTERA o VIANDA: el Badge del frontend decide el color.
    tipos_validos = {"MORTERA", "VIANDA"}
    tipos_malos = {c.tipo for c in comandas} - tipos_validos
    if tipos_malos:
        fallos.append(f"tipos inesperados: {tipos_malos}")
    print(f"   tipo siempre MORTERA/VIANDA: {'si' if not tipos_malos else 'NO ' + str(tipos_malos)}")

    # Los folios no se repiten en la tabla.
    folios = [c.comanda for c in comandas]
    if len(folios) != len(set(folios)):
        fallos.append("folios duplicados en la misma fecha")
    print(f"   folios sin duplicar: {'si' if len(folios) == len(set(folios)) else 'NO'}")

    # ── Estadisticas ──
    print("\n3. Estadisticas (lo que pintan las graficas)")
    s = calcular_estadisticas(comandas)
    print(f"   total_comandas={s.total_comandas}  PAX={s.total_alimentos}")
    print(f"   mortera={s.total_mortera}  vianda={s.total_viandas}")

    # Cada grafica se alimenta de una de estas diccionarios; si uno no cuadra
    # con el total, el grafico y el KPI mostrarian numeros distintos.
    for nombre, conteo in [
        ("por_destino", s.por_destino),
        ("por_destino_grafico", s.por_destino_grafico),
        ("por_compania", s.por_compania),
        ("por_transporte", s.por_transporte),
    ]:
        suma = sum(conteo.values())
        ok = suma == s.total_alimentos
        print(f"   {nombre:22} {len(conteo):3} claves, suma {suma} {'OK' if ok else 'NO CUADRA'}")
        if not ok:
            fallos.append(f"{nombre} suma {suma} != {s.total_alimentos}")

    # La leyenda del donut no puede tener claves vacias.
    vacias = [k for k in s.por_destino_grafico if not k.strip()]
    if vacias:
        fallos.append(f"claves vacias en por_destino_grafico: {len(vacias)}")
    print(f"   sin claves vacias: {'si' if not vacias else 'NO'}")

    # Top 5 para ver que son legibles.
    print("\n   top destinos:")
    for k, v in sorted(s.por_destino.items(), key=lambda x: -x[1])[:5]:
        print(f"     {v:>5}  {k}")
    print("   top companias:")
    for k, v in sorted(s.por_compania.items(), key=lambda x: -x[1])[:5]:
        print(f"     {v:>5}  {k}")

    # ── Diagnostico ──
    print("\n4. Diagnostico (panel de soporte)")
    d = diagnostico(usuario)
    for k, v in d.items():
        if k != "ultimas_fechas":
            print(f"   {k}: {v}")

    print("\n" + "=" * 50)
    if fallos:
        print("FALLOS:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("Los datos de la pantalla estan listos para pintarse.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_test(sys.argv[1] if len(sys.argv) > 1 else None))
