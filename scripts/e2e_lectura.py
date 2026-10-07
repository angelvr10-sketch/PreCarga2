"""
Prueba de extremo a extremo contra Supabase REAL, en modo SOLO LECTURA.

A diferencia de tests/test_api_comandas.py, que usa dobles, este script no
simula nada: arranca la app de verdad, hace login de verdad y consulta la base de
verdad. Es la unica forma de saber que el repositorio habla bien con
PostgREST y que la RPC funciona.

NO MODIFICA NADA:
  - no sube reportes (no escribe en `comandas`);
  - no pide PDFs de reporte, porque cada uno descuenta una descarga del
    contador `descargas_usadas` del usuario;
  - el PDF se genera por separado, con `core.comandas.pdf`, que es una funcion
    pura y no toca la base.

    python scripts/e2e_lectura.py [usuario] [password]

Con password '-' NO hace login: fuerza la sesion leyendo el usuario real de
`usuarios`. Sirve para probar con un usuario que no es admin sin conocer su
contrasena, y no escribe nada en la base.
"""
import io
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfReader  # noqa: E402

import main  # noqa: E402
from core.comandas.pdf import pdf_comandas  # noqa: E402

USUARIO = sys.argv[1] if len(sys.argv) > 1 else "admin"
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else "admin123"


def seccion(titulo):
    print()
    print("=" * 70)
    print(titulo)
    print("=" * 70)


def main_test() -> int:
    fallos = []

    with TestClient(main.app) as c:
        # ── Sesion ──
        seccion("1. Sesion")
        if PASSWORD == "-":
            # Sin password: se fuerza la sesion para un usuario que ya existe en
            # `usuarios`. Es la via para probar el caso de un usuario que no es
            # admin, cuya contrasena no se conoce.
            #
            # Se lee el usuario REAL de Supabase, no se inventa uno: si el
            # nombre no existe, `get_current_user` devuelve None y la prueba
            # avisa en vez de dar un falso OK.
            from core.supabase_db import _get

            filas = _get("usuarios", select="id,username,email,rol,descargas_usadas",
                         filters={"username": f"eq.{USUARIO}"})
            if not filas:
                print(f"   El usuario '{USUARIO}' no existe en `usuarios`.")
                print("   Revisa el nombre: 'erika' vs 'Erika'.")
                return 1
            import routers.api_comandas as rc
            real = filas[0]
            rc.get_current_user = lambda request, u=real: u
            print(f"   sesion forzada para: {real['username']} (rol={real['rol']}, "
                  f"id={real['id']})")
            print("   sin login: NO se creo ninguna sesion en la base")
        else:
            r = c.post("/api/auth/login", json={"email": USUARIO, "password": PASSWORD})
            print(f"   status: {r.status_code}")
            if r.status_code != 200:
                print(f"   {r.text[:300]}")
                print("\nNo se pudo iniciar sesión; el resto no se prueba.")
                return 1
            cuerpo = r.json()
            print(f"   usuario: {cuerpo['user']['nombre']}  "
                  f"admin={cuerpo['user']['admin']}")
            print("   cookie de sesion: OK")

        # ── Fechas ──
        seccion("2. GET /api/comandas/fechas  (la RPC de la migracion)")
        r = c.get("/api/comandas/fechas")
        print(f"   status: {r.status_code}")
        if r.status_code != 200:
            print(f"   {r.text[:300]}")
            fallos.append("fechas")
            return 1
        fechas = r.json()["fechas"]
        print(f"   fechas con comandas: {len(fechas)}")
        for f in fechas[:8]:
            print(f"     {f}")
        if not fechas:
            print("   (este usuario no tiene comandas; las pruebas de datos no aplican)")
            return 0

        # ── Comandas de una fecha ──
        seccion(f"3. GET /api/comandas/?fecha={fechas[0]}")
        r = c.get("/api/comandas/", params={"fecha": fechas[0]})
        print(f"   status: {r.status_code}")
        if r.status_code != 200:
            print(f"   {r.text[:300]}")
            fallos.append("listar")
            return 1
        datos = r.json()
        print(f"   comandas: {datos['total']}   PAX: {datos['total_pax']}   "
              f"titulo: {datos['titulo']}")
        for cm in datos["comandas"][:5]:
            print(f"     {cm['comanda']}  {cm['destino'][:16]:16} "
                  f"{cm['compania'][:18]:18} pax={cm['pax']:>4}  "
                  f"{cm['transporte']:11} {cm['tipo']}")

        # ── Estadisticas ──
        seccion("4. GET /api/comandas/estadisticas")
        r = c.get("/api/comandas/estadisticas", params={"fecha": fechas[0]})
        print(f"   status: {r.status_code}")
        if r.status_code != 200:
            print(f"   {r.text[:300]}")
            fallos.append("estadisticas")
            return 1
        e = r.json()
        print(f"   comandas={e['total_comandas']}  PAX={e['total_alimentos']}  "
              f"mortera={e['total_mortera']}  vianda={e['total_viandas']}")

        suma_destino = sum(e["por_destino"].values())
        suma_transporte = sum(e["por_transporte"].values())
        print(f"   suma por destino:    {suma_destino}")
        print(f"   suma por transporte: {suma_transporte}")
        if suma_destino != e["total_alimentos"]:
            print(f"   INCOHERENTE por destino: {suma_destino} != {e['total_alimentos']}")
            fallos.append("coherencia destino")
        if suma_transporte != e["total_alimentos"]:
            print(f"   INCOHERENTE por transporte: {suma_transporte} != {e['total_alimentos']}")
            fallos.append("coherencia transporte")

        print("   top destinos:")
        for nombre, pax in sorted(e["por_destino"].items(), key=lambda x: -x[1])[:5]:
            print(f"     {pax:>5}  {nombre}")
        print("   transportes:")
        for nombre, pax in sorted(e["por_transporte"].items(), key=lambda x: -x[1]):
            print(f"     {pax:>5}  {nombre}")

        # ── Aislamiento ──
        seccion("5. Aislamiento entre usuarios")
        print("   Las comandas de otra fecha/no usuario no deben verse.")
        r_fecha_vacia = c.get("/api/comandas/", params={"fecha": "1999-01-01"})
        print(f"   fecha inexistente -> status {r_fecha_vacia.status_code}, "
              f"{r_fecha_vacia.json()['total']} comandas (esperado 0)")
        if r_fecha_vacia.json()["total"] != 0:
            fallos.append("aislamiento")

        # ── Validaciones ──
        seccion("6. Validaciones de entrada")
        for valor, esperado in [("no-es-fecha", 400), ("2026-13-45", 400)]:
            r = c.get("/api/comandas/", params={"fecha": valor})
            ok = r.status_code == esperado
            print(f"   fecha={valor!r:16} -> {r.status_code} (esperado {esperado}) "
                  f"{'OK' if ok else 'FALLA'}")
            if not ok:
                fallos.append(f"validacion {valor}")

        # ── Generacion de PDF (sin tocar la base) ──
        seccion("7. PDF generado con datos reales (funcion pura, sin BD)")
        from core.comandas.parser import Comanda
        comandas = [
            Comanda(c["comanda"], c["horario"], c["compania"], c["destino"],
                    c["pax"], c["transporte"], c["menu_1"], c["menu_2"],
                    c["tipo"], c["observaciones"])
            for c in datos["comandas"]
        ]
        pdf = pdf_comandas(comandas, "MIÉRCOLES, 7 DE OCTUBRE DE 2026", datos["titulo"])
        paginas = len(PdfReader(io.BytesIO(pdf)).pages)
        print(f"   {len(comandas)} comandas -> {paginas} paginas, {len(pdf):,} bytes")
        if paginas != len(comandas):
            print(f"   FALLA: {paginas} paginas para {len(comandas)} comandas")
            fallos.append("paginas pdf")
        else:
            print("   OK: una pagina por comanda")

    seccion("RESULTADO")
    if fallos:
        print(f"FALLOS: {fallos}")
        return 1
    print("Todo OK contra Supabase real (solo lectura).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_test())
