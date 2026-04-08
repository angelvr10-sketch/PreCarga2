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
RUTA_COMPANIAS        = LIB_DIR / "companias.csv"
RUTA_ACTIVOS          = LIB_DIR / "activos.csv"
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
