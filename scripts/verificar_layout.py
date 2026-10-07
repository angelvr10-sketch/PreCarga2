"""
Comprobacion del LAYOUT de /comandas con datos reales, sin navegador.

El navegador sirve para ver si algo se rompe; para lo de verdad importante aqui
—que el contenido no desborde en pantallas angostas y que los grids se
pilen bien— lo que se necesita son los clases de Tailwind que se aplican y el
ancho disponible.

Sin las utilidades generadas no se puede medir nada, asi que lo que se hace es
lo mas simple y mas util: comprobar que las CLASES de responsive que se
escribieron existen en el CSS compilado. Si `xl:grid-cols-6` no aparece en el
CSS, es que la clase esta mal escrita y Tailwind no la genero: el grid no se
pila y la pagina se ve rota en movil sin que nadie se entere.

    python scripts/verificar_layout.py
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "frontend" / "dist"
sys.stdout.reconfigure(encoding="utf-8")

# Clases que DEBEN existir en el CSS compilado, con el breakpoint que las activa.
# `md:` 768px, `lg:` 1024px, `xl:` 1280px.
ESPERADAS = {
    # 6 KPIs en una fila en pantalla grande, 2 en movil.
    "grid-cols-2": "KPI: 2 columnas en movil",
    "md:grid-cols-3": "KPI: 3 columnas en tablet",
    "xl:grid-cols-6": "KPI: 6 columnas en escritorio",
    # Graficas + tablas: 1 columna en movil, 2 en tablet, 3 en escritorio.
    "lg:grid-cols-2": "graficas/tablas: 2 columnas en tablet",
    "xl:grid-cols-[1fr_1fr_1.1fr]": "graficas/tablas: 3 columnas en escritorio",
    # Fecha y subida apiladas en movil.
    "lg:grid-cols-[minmax(0,340px)_1fr]": "encabezado: 2 columnas en escritorio",
    # Botones de reporte.
    "sm:grid-cols-2": "reportes: 2 columnas en movil grande",
    "xl:grid-cols-4": "reportes: 4 columnas en escritorio",
}


def _escapar(clase: str) -> str:
    """Como Tailwind escribe una clase en el CSS: `md:grid-cols-3` sale
    `.md\\:grid-cols-3`, y las utilidades con corchetes escapan tambien los
    caracteres internos.

    Buscar el texto plano NO encuentra nada, que es lo que hacia la primera
    version de este script: daba FALTA para clases que si existian.
    """
    salida = ""
    for ch in clase:
        if ch.isalnum() or ch in "-_":
            salida += ch
        else:
            salida += "\\" + ch
    return salida


def main() -> int:
    css_files = list((DIST / "assets").glob("*.css"))
    if not css_files:
        print(f"No hay CSS compilado en {DIST / 'assets'}.")
        print("Corre `npm run build` en frontend/ primero.")
        return 1

    css = "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in css_files)
    print(f"CSS compilado: {len(css_files)} archivo(s), {len(css):,} caracteres\n")

    faltan = []
    for clase, para_que in ESPERADAS.items():
        # Tailwind escribe la clase como `.md\:grid-cols-3{...}`, con el `:` y
        # los corchetes escapados con barra invertida.
        escapada = _escapar(clase)
        encontrada = f".{escapada}" in css or f".{escapada.replace(chr(92), '')}" in css

        marca = "OK  " if encontrada else "FALTA"
        if not encontrada:
            faltan.append(clase)
        print(f"  {marca} {clase:32} {para_que}")

    print()
    if faltan:
        print("CLASES QUE NO ESTAN EN EL CSS:")
        for c in faltan:
            print(f"  - {c}")
        print("\nSi una falta, Tailwind no la genero: la utilidad esta mal escrita")
        print("y el layout no responde en esa pantalla.")
        return 1

    print("Todas las clases de responsive existen en el CSS compilado.")

    # ── Comprobacion de que no haya utilidades invertidas ──
    print("\nComprobando que no haya 'lg:' en algo que deberia ser movil...")
    # Un fallo tipico es dejar un grid de 3 columnas sin breakpoint, que en
    # movil se convierte en 3 columnas estrechas.
    rutas = list((DIST / "assets").glob("comandas-*.js"))
    if rutas:
        js = rutas[0].read_text(encoding="utf-8", errors="replace")
        # Busca grids de N>2 columnas que NO esten prefijados por un breakpoint.
        sueltos = re.findall(r'"grid-cols-([3-9]|1[0-2])(?![-\w])', js)
        if sueltos:
            print(f"  AVISO: hay grid-cols-{sueltos[0]} sin breakpoint en la ruta.")
            print("  En movil eso son N columnas estrechas. Deberia tener lg: o xl:.")
        else:
            print("  OK: ningun grid de 3+ columnas sin breakpoint.")
    else:
        print("  (no se encontro el chunk de comandas)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
