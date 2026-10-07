"""
El parser, de punta a punta, sobre los PDF reales de la plataforma.

`tests/test_fixtures_reales.py` mira el regex suelto. Aqui se usa el pipeline
completo (`parse_pdf` -> `calcular_estadisticas`) sobre los reportes de ENTRADA,
que es lo que el usuario sube, y se imprime lo mismo que vera en pantalla.

    python scripts/probar_pipeline.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from core.comandas.parser import parse_pdf, ErrorProcesandoPDF  # noqa: E402
from core.comandas.stats import calcular_estadisticas  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
ARCHIVOS = ["ComandaAlimentos.pdf", "ComandaAlimentos(1).pdf", "ComandaAlimentos(2).pdf"]


def main() -> int:
    fallos = 0

    for nombre in ARCHIVOS:
        ruta = FIXTURES / nombre
        if not ruta.is_file():
            print(f"[falta] {ruta}")
            continue

        print("=" * 74)
        print(f"{nombre}")
        print("=" * 74)

        try:
            r = parse_pdf(ruta.read_bytes())
        except ErrorProcesandoPDF as exc:
            print(f"  ERROR: {exc}")
            fallos += 1
            continue

        s = calcular_estadisticas(r.comandas)

        print(f"  comandas:     {len(r.comandas)}")
        print(f"  fecha_iso:    {r.fecha_iso}")
        print(f"  fecha_texto:  {r.fecha_texto}")
        print(f"  titulo:       {r.titulo}")
        print(f"  total PAX:    {r.total_pax}")
        print()
        print(f"  morteras:     {s.total_mortera}")
        print(f"  viandas:      {s.total_viandas}")
        print(f"  transportes:  {s.por_transporte}")
        print()

        top_dest = sorted(s.por_destino.items(), key=lambda x: -x[1])[:6]
        print("  top destinos:")
        for d, pax in top_dest:
            print(f"    {pax:>5}  {d}")

        top_comp = sorted(s.por_compania.items(), key=lambda x: -x[1])[:6]
        print("  top companias:")
        for c, pax in top_comp:
            print(f"    {pax:>5}  {c}")

        if r.advertencias:
            print()
            print("  ADVERTENCIAS:")
            for a in r.advertencias:
                print(f"    - {a}")

        # Coherencia de las sumas.
        if s.total_alimentos != r.total_pax:
            print(f"\n  INCOHERENTE: stats={s.total_alimentos} vs parse={r.total_pax}")
            fallos += 1
        print()

    print("\n" + ("PIPELINE OK" if not fallos else f"{fallos} fallo(s)"))
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
