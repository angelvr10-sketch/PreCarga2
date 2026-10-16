"""core/config.py — Configuración centralizada"""
from pathlib import Path
import logging
from datetime import datetime

BASE_DIR   = Path(__file__).parent.parent
LIB_DIR    = BASE_DIR / "lib"
SOL_DIR    = BASE_DIR / "solicitudes"
LOGS_DIR   = BASE_DIR / "logs"

RUTA_PLANTILLA        = LIB_DIR / "plantilla.xlsx"
RUTA_PLANTILLA_SALIDA = LIB_DIR / "salida.xlsx"
RUTA_PLANTILLA_ENTRADA= LIB_DIR / "entrada.xlsx"

# ────────────────────────────────────────────────────────────────
#  Ventana de las gráficas del dashboard
# ────────────────────────────────────────────────────────────────
# Dias que las graficas muestran POR DELANTE de hoy, ademas del periodo pedido.
#
# Vive aqui, y no duplicado en cada ventana, porque las graficas del dashboard
# comparten el mismo selector de periodo: `core/comandas/serie.py::ventana` (la
# de Comandas por barco) y `routers/api_data.py::_agregar_ultimos_dias` (Altas vs
# Bajas y las barras RPX/CPZ). Si cada una redondeara por su cuenta, el mismo
# selector acabaria moviendo dos ventanas distintas y la comparacion entre
# graficas seria falsa, que es justo lo que `tests/test_serie.py` vigila.
#
# Por que dias hacia adelante y no recortar el historico: la ventana se ALARGA.
# Con 30 dias se siguen viendo los mismos 30 dias de historia y se suman 2 al
# final. Recortar en vez de alargar dejaria fuera los 2 dias mas recientes, que
# es informacion que hoy si se ve.
#
# Los dias futuros salen en cero: `solicitudes.fecha_llegada` y
# `comandas.fecha_registro` nunca estan en el futuro, asi que no inventan datos,
# solo reservan el espacio del eje X donde caera la actividad de mañana.
DIAS_FUTURO = 2

# `companias.csv` y `activos.csv` se dejaron de usar el 2026-10-07: la UI escribe
# en Supabase y el procesador leia el CSV, asi que cualquier alta desde la app era
# invisible. Ahora los dos catalogos salen de la base (ver core/catalogo.py).
# Los archivos se conservan en lib/ solo como respaldo historico.
MAPEO_ACTIVOS = {
    "COORDINACION DE SERVICIOS MARINOS Y DE MANTENIMIENTO":
        "COORDINACION DE SERVICIOS MARINOS Y DE MANTENIMIENTO, CONFIABILIDAD Y CONSTRUCCION DE INFRAESTRUCTURA",
    "GERENCIA DE MANTENIMIENTO ESTATICO E INFRAESTRUCTURA":
        "GERENCIA DE MANTENIMIENTO ESTATICO E INFRAESTRUCTURA COMPLEMENTARIA MARINA"
}

for d in [LIB_DIR, SOL_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Logging
log_file = LOGS_DIR / f"precarga_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("precarga")
