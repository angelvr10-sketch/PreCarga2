"""
EL TEST DEFINITIVO: el PDF que genera el modulo nuevo contra el PDF que genero
la app original.

`tests/fixtures/Todas_las_Comandas_REFORMA_PEMEX.pdf` son 30 paginas del machote
que produjo ComandasPro el 2026-10-06: 30 comandas de REFORMA PEMEX para el
miercoles 7 de octubre de 2026.

Aqui no se comparan textos sueltos sino GEOMETRIA REAL DE PAGINA. De cada
pagina se saca la posicion (x, y) de cada linea de texto y se leen del golden
las comandas que describe; despues se vuelven a dibujar con el modulo nuevo y se
comparan las coordenadas.

Eso es mas fuerte que comparar texto: si una linea de firma se mueve medio
milimetro, el texto puede seguir coincidiendo y aqui se nota.

Detalle tecnico: reportlab dibuja las tablas de `platypus` bajo una matriz de
transformacion (CTM), asi que las coordenadas del `tm` del visor de pypdf son
LOCALES a esa matriz. Hay que aplicar la CTM para obtener la posicion real en
la pagina, que es la que se compara.

    python scripts/comparar_golden.py
"""
import io
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8")

from pypdf import PdfReader  # noqa: E402

from core.comandas.parser import Comanda  # noqa: E402
from core.comandas.pdf import pdf_comandas  # noqa: E402

GOLDEN = RAIZ / "tests" / "fixtures" / "Todas_las_Comandas_REFORMA_PEMEX.pdf"

TITULO = "REFORMA PEMEX"
FECHA = "MIÉRCOLES, 7 DE OCTUBRE DE 2026"

# Rangos x de cada columna de la tabla de datos. La tabla se dibuja con
# colWidths [100, 195, 90, 60, 60] y margen (612 - 505) / 2 = 53.5, asi que las
# columnas empiezan en 53.5, 153.5, 348.5, 438.5 y 498.5. Los centroides
# medidos sobre el golden caen dentro de esos rangos.
COL_DESTINO = (0.0, 153.5)
COL_COMPANIA = (153.5, 348.5)
COL_PAX = (348.5, 438.5)
COL_MENU1 = (438.5, 498.5)
COL_MENU2 = (498.5, 612.0)

ETIQUETAS = {
    "DESTINO", "DEPARTAMENTO/COMPAÑÍA", "NO. PERSONAS", "MENU 1", "MENU 2",
    "SALIDA", "DEVOLUCIÓN", "DESCRIPCION", "CANTIDAD", "OBSERVACIONES:",
}

# Tolerancia al comparar. reportlab emite floats; el redondeo a 0.1 pt
# (0.035 mm) ya es mas fino que el grosor de un pelo.
TOL = 0.1


def runs(pagina):
    """[(x_abs, y_abs, texto)] de una pagina, con la CTM aplicada."""
    out = []

    def visitor(text, cm, tm, fd, fs):
        t = text.strip()
        if not t:
            return
        x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
        y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
        out.append((round(x, 1), round(y, 1), t))

    pagina.extract_text(visitor_text=visitor)
    return out


def lineas(items):
    """Agrupa los runs por fila y los ordena de izquierda a derecha.

    Comparar linea por linea en vez de fragmento por fragmento es lo que hace la
    comparacion estable: dos PDFs pueden partir el mismo texto en trozos
    distintos y aun asi dibujar la pagina identica.
    """
    filas = {}
    for x, y, t in items:
        clave = round(y / 2.0) * 2.0        # agrupa lo que esta en la misma linea
        filas.setdefault(clave, []).append((x, y, t))
    return [
        (y, " ".join(t for _, _, t in sorted(xs, key=lambda z: z[0])))
        for y, xs in sorted(filas.items(), key=lambda kv: -kv[0])
    ]


def _en(rango, x):
    return rango[0] <= x < rango[1]


def leer_comanda(items):
    """Deduce la comanda de una pagina a partir de la geometria.

    Cada bloque del machote ocupa una franja vertical propia, y las franjas son
    las mismas en las 30 paginas. Se delimitan con dos anclas que el propio
    machote dibuja: 'SALIDA' (arriba de las tablas de utensilios) y
    'NO. PERSONAS' (la cabecera de la tabla de datos).
    """
    y_salida = next((y for x, y, t in items if t == "SALIDA"), 0)
    y_tabla = next((y for x, y, t in items if t == "NO. PERSONAS"), 0)
    y_obs = next((y for x, y, t in items if t == "OBSERVACIONES:"), None)

    folio = fecha = titulo = ""
    observaciones = ""
    destino = compania = ""
    pax = menu_1 = menu_2 = 0

    # Valores de la tabla: entre 'SALIDA' y la cabecera.
    for x, y, t in items:
        if y_salida <= y < y_tabla and t not in ETIQUETAS:
            if re.fullmatch(r'\d{1,3}', t):
                if _en(COL_PAX, x) and not pax:
                    pax = int(t)
                elif _en(COL_MENU1, x) and not menu_1:
                    menu_1 = int(t)
                elif _en(COL_MENU2, x):
                    menu_2 = int(t)
            elif _en(COL_DESTINO, x):
                destino = f"{destino} {t}".strip()
            elif _en(COL_COMPANIA, x):
                compania = f"{compania} {t}".strip()

    # Observaciones: las lineas entre la cabecera de la tabla y la etiqueta.
    if y_obs is not None:
        for x, y, t in items:
            if y_tabla <= y < y_obs and not re.fullmatch(r'[A-Z]{3}\d+', t) \
                    and t not in ETIQUETAS:
                observaciones = f"{observaciones} {t}".strip()

    # Encabezado: todo lo que queda por encima de la tabla. La condicion se
    # escribe con un if explicito porque `if y <= y_obs if ... else ...` se
    # parsea como una ternaria y no como lo que parece.
    if y_obs is not None:
        zona_alta = y <= y_obs
    else:
        zona_alta = y >= y_tabla

    for x, y, t in items:
        if zona_alta:
            if re.fullmatch(r'[A-Z]{3}\d+', t) and not folio:
                folio = t
            elif re.match(r'[A-ZÁÉÍÓÚÑ]+,\s*\d{1,2}\s+DE\s', t):
                fecha = t
            elif t in ("REFORMA PEMEX", "CERRO DE LA PEZ", "ALIMENTOS AL AREA"):
                titulo = t

    if not folio:
        raise ValueError("no se encontro el folio")

    return {
        "folio": folio, "fecha": fecha, "titulo": titulo,
        "destino": destino, "compania": compania,
        "pax": pax, "menu_1": menu_1, "menu_2": menu_2,
        "observaciones": observaciones,
    }


def comparar_lineas(a, b):
    """Diferencias entre dos listas de (y, texto)."""
    if len(a) != len(b):
        return [f"numero de lineas: golden {len(a)}, nuevo {len(b)}"]
    out = []
    for i, ((ya, ta), (yb, tb)) in enumerate(zip(a, b)):
        if ta != tb or abs(ya - yb) > TOL:
            out.append(f"  linea {i + 1}: golden y={ya} {ta!r}")
            out.append(f"            nuevo  y={yb} {tb!r}")
    return out


def main() -> int:
    if not GOLDEN.is_file():
        print(f"[falta] {GOLDEN}")
        return 0

    lector = PdfReader(GOLDEN)
    print(f"Golden: {GOLDEN.name}  ({len(lector.pages)} paginas)\n")

    comandas, leidas, errores = [], [], []
    for i, pagina in enumerate(lector.pages):
        try:
            d = leer_comanda(runs(pagina))
        except Exception as exc:
            errores.append(f"pagina {i + 1}: {exc}")
            continue
        leidas.append(d)
        comandas.append(Comanda(
            comanda=d["folio"], horario="06:00", compania=d["compania"],
            destino=d["destino"], pax=d["pax"], transporte="GANGWAY",
            menu_1=d["menu_1"], menu_2=d["menu_2"], tipo="VIANDA",
            observaciones=d["observaciones"],
        ))

    for e in errores:
        print(f"  {e}")
    print(f"\nComandas deducidas del golden: {len(comandas)}")

    if not comandas:
        return 1

    print("\nMuestra de lo leido:")
    for d in leidas[:6]:
        print(f"  {d['folio']}  {d['destino'][:14]:14} {d['compania'][:14]:14} "
              f"pax={d['pax']:>3} m1={d['menu_1']:>3} m2={d['menu_2']:>3}  "
              f"{d['observaciones'][:32]}")

    fechas = {d["fecha"] for d in leidas}
    titulos = {d["titulo"] for d in leidas}
    print(f"\nFechas leidas en las 30 paginas: {fechas}")
    print(f"Titulos leidos: {titulos}")
    print(f"Total PAX leido: {sum(c.pax for c in comandas)}")
    print(f"Total menu 1:   {sum(c.menu_1 for c in comandas)}")
    print(f"Total menu 2:   {sum(c.menu_2 for c in comandas)}\n")

    # ── Regenerar y comparar ──
    pag_nuevas = PdfReader(io.BytesIO(pdf_comandas(comandas, FECHA, TITULO))).pages
    pag_viejas = lector.pages

    print(f"Golden: {len(pag_viejas)} paginas   Nuevo: {len(pag_nuevas)} paginas")
    if len(pag_nuevas) != len(pag_viejas):
        print("DIFIERE el numero de paginas")
        return 1

    iguales, diferencias = 0, []
    for i, (pv, pn) in enumerate(zip(pag_viejas, pag_nuevas)):
        dif = comparar_lineas(lineas(runs(pv)), lineas(runs(pn)))
        if not dif:
            iguales += 1
        else:
            diferencias.append((i + 1, dif))

    print(f"\nPaginas IDENTICAS (texto y posicion): {iguales}/{len(pag_viejas)}")

    if diferencias:
        print(f"\nPaginas con diferencias: {[n for n, _ in diferencias]}")
        for n, dif in diferencias[:2]:
            print(f"\n--- Pagina {n} ---")
            for d in dif[:24]:
                print(d)

    return 0 if not diferencias else 1


if __name__ == "__main__":
    raise SystemExit(main())
