"""
Fixtures compartidos.

Se anade la raiz del proyecto a sys.path para que `import core` funcione al
correr pytest desde precarga2/ sin instalar el paquete.
"""
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Carpeta de PDFs reales. Vacia por ahora: cuando haya reportes de la
# plataforma, se copian aqui y los tests de abajo los usan de golden set.
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURES.mkdir(exist_ok=True)


@pytest.fixture(scope="session", autouse=True)
def _sin_verificacion_de_bd_al_arrancar():
    """Anula `init_db()` y familia en el arranque de la app.

    `main.startup()` pega a Supabase tres veces (usuarios, solicitudes, pagos). Con
    `TestClient(main.app)` eso se repite en CADA test que levanta el contexto, y
    son casi 100: la suite se iba a mas de un minuto solo en esperas de red.

    Es global y no por modulo porque la causa es del arrancque de la app, no de
    ningun test: aqui no hay nada que verificar porque no se levanta nada real.

    Ademas, antes esto era obligatorio de forma indirecta. `supabase_db.cerrar_cliente()`
    (que corre en el `shutdown`) dejaba `_CLIENT = None` y la siguiente peticion
    fallaba con "httpx no esta instalado" sin abrir nada. La suite era rapida porque
    el pool estaba MUERTO y los arranques fallaban de inmediato; al arreglar el
    error (el pool ahora se reabre solito) quedo a la vista que cada arranque
    estaba haciendo red de verdad.

    Ningun test depende de estas funciones: la sesion se falsea con
    `get_current_user` o `get_user_from_token`, no con la base.
    """
    import main

    main.init_db = lambda: None
    main.init_solicitudes_db = lambda: None
    main.init_stripe_payments_db = lambda: None


@pytest.fixture
def comanda():
    """Constructor de Comanda con valores por defecto, para no repetir."""
    from core.comandas.parser import Comanda

    def _make(folio="ABC123", **kwargs):
        datos = {
            "comanda": folio,
            "horario": "08:30",
            "compania": "KOL TOV",
            # OJO: el destino del parser va SIN espacios ('PAPALOAPAN'), porque
            # es como esta en la lista de destinos. Un destino con espacio que no
            # este en la lista NO se reconoce y el parser no ve la comanda.
            "destino": "PAPALOAPAN",
            "pax": 10,
            "transporte": "GANGWAY",
            "menu_1": 10,
            "menu_2": 0,
            "tipo": "VIANDA",
            "observaciones": "",
        }
        datos.update(kwargs)
        return Comanda(**datos)

    return _make


@pytest.fixture
def varias_comandas(comanda):
    """12 comandas mezclando mortera y vianda, para los que cuentan paginas."""
    return [
        comanda(
            f"CMN{i:03d}",
            destino="PAPALOAPAN",
            tipo="MORTERA" if i % 3 == 0 else "VIANDA",
            pax=10 + i,
            menu_1=10 + i,
            menu_2=i % 4,
            compania=f"COMPAÑIA {i % 5}",
        )
        for i in range(12)
    ]
