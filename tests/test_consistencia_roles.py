"""
El invariante que se rompio: lo que la UI ofrece tiene que ser EXACTAMENTE lo
que el backend permite.

En F5, `useReportesDisponibles` recibia `esLector = !esAdmin` yumniaba a
todo usuario que no fuera admin. En precarga2 los roles son `admin` y `usuario`,
y `usuario` NO es lector. Resultado: a `erika` le salia un solo boton de los
cuatro, aunque el backend le permitia los cuatro. Nadie se dio cuenta hasta que
ella lo uso.

La UI y el backend viven en archivos distintos (TypeScript y Python) y no se
pueden ver entre si en tiempo de ejecucion, asi que nada evita que se
desincronicen. Este test es lo que lo evita: lee la constante del backend y la
regla del frontend y comprueba que dicen lo mismo.

Es un test de FUENTES, no de comportamiento, a proposito: comprueba lo que nadie
puede comprobar en caliente.

    tests/test_consistencia_roles.py
"""
import re
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from routers.api_comandas import ROLES_LECTURA, ROLES_REPORTE_COMPLETO

HOOK = RAIZ / "frontend" / "src" / "hooks" / "use-comandas.ts"
AUTH = RAIZ / "routers" / "api_auth.py"
TYPES = RAIZ / "frontend" / "src" / "types" / "index.ts"

pytestmark = pytest.mark.skipif(
    not HOOK.is_file(),
    reason=f"No se encuentra {HOOK}",
)


# ── Los dos lados de la regla ──────────────────────────────────

def _roles_completos_desde_backend() -> set[str]:
    return set(ROLES_REPORTE_COMPLETO)


def _rol_excluido_en_frontend() -> str | None:
    """El frontend decide con una comparacion literal: `if (normalizado === 'lector')`.

    O sea: TODO rol que no sea ese entra. Devuelve el rol excluido, o None si
    la forma del hook cambio y el test debe avisar en vez de pasar en falso.
    """
    fuente = HOOK.read_text(encoding="utf-8")
    m = re.search(
        r"if\s*\(\s*normalizado\s*===\s*['\"]([a-z_]+)['\"]\s*\)\s*return",
        fuente,
    )
    return m.group(1) if m else None


class TestInvarianteDeRoles:

    def test_el_hook_sigue_reconocible(self):
        """Si alguien reescribe la regla del hook, este test debe FALLAR para
        que se actualice a mano. Es preferible un falso positivo a un
        invariante que dejo de comprobarse en silencio."""
        assert _rol_excluido_en_frontend() is not None, (
            "No se encontro la regla del frontend. Si cambiaste como decide "
            "useReportesDisponibles, actualiza este test."
        )

    def test_frontend_y_backend_coinciden(self):
        """El frontend deja pasar a todo rol que no sea el excluido; el backend
        solo a los de ROLES_REPORTE_COMPLETO. Tiene que ser el mismo conjunto."""
        excluido = _rol_excluido_en_frontend()
        assert excluido is not None

        backend = _roles_completos_desde_backend()
        assert excluido not in backend, (
            f"El frontend excluye a '{excluido}' pero el backend si lo acepta en "
            f"ROLES_REPORTE_COMPLETO. Ese rol veria botones que fallan con 403."
        )

        # El caso que se rompio: 'usuario' NO es lector.
        assert "usuario" in backend, (
            "El backend dejo de aceptar 'usuario'. Si es a proposito, hay que "
            "cambiar tambien el frontend."
        )
        assert excluido != "usuario", (
            "'usuario' no puede tratarse como lector: en precarga2 es el rol de "
            "todo usuario normal. Tratarlo como lector隐藏 los reportes que si "
            "le tocan. Este fue el bug."
        )

    def test_lector_existe_en_el_backend_pero_no_en_completo(self):
        """`lector` esta en ROLES_LECTURA pero no en ROLES_REPORTE_COMPLETO: puede
        ver el dashboard y descargar una comanda suelta, pero no generar los
        reportes en bloque. Es el sentido de la diferencia entre las dos listas."""
        assert "lector" in ROLES_LECTURA
        assert "lector" not in ROLES_REPORTE_COMPLETO


class TestElRolExponeElDetalle:

    def test_auth_me_incluye_el_rol(self):
        """Sin `rol` en la respuesta, el frontend no puede distinguir 'usuario'
        de 'lector' y vuelve a caer en tratar a todos como lectores."""
        fuente = AUTH.read_text(encoding="utf-8")
        bloque = re.search(
            r"def _serialize_user.*?return\s*\{(.*?)\}", fuente, re.S
        )
        assert bloque, "No se encontro _serialize_user en routers/api_auth.py"
        assert '"rol"' in bloque.group(1), (
            "_serialize_user no expone 'rol'. El frontend lo necesita para "
            "decidir que reportes mostrar."
        )

    def test_el_tipo_de_usuario_declara_el_rol(self):
        fuente = TYPES.read_text(encoding="utf-8")
        bloque = re.search(r"interface Usuario\s*\{(.*?)\n\}", fuente, re.S)
        assert bloque, "No se encontro la interface Usuario"
        assert re.search(r"^\s*rol:\s*string", bloque.group(1), re.M), (
            "El tipo Usuario no declara `rol`; TypeScript no obligaria a usarlo."
        )

    def test_la_pagina_usa_el_rol_y_no_el_booleano(self):
        """La pagina debe pasar `user.rol` al hook, no `!user.admin`."""
        pagina = (RAIZ / "frontend" / "src" / "routes" / "comandas.tsx").read_text(
            encoding="utf-8"
        )
        assert "useReportesDisponibles(user?.rol" in pagina, (
            "comandas.tsx debe pasar el rol crudo a useReportesDisponibles. "
            "Si vuelve a pasar un booleano, se repite el bug de ocultar los "
            "reportes a los usuarios normales."
        )
        assert "esLector = !esAdmin" not in pagina, (
            "No se puede deducir 'lector' de 'no es admin': 'usuario' no es lector."
        )
