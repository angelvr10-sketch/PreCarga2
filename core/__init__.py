from .procesador import (
    llenar_plantilla, extraer_personal_baja, guardar_csv_baja,
    listar_archivos_baja, listar_solicitudes_xlsx, leer_meta_xlsx,
    leer_meta_baja, llenar_plantilla_salidas, llenar_plantilla_entrada,
    leer_personal_de_xlsx,
)
from .catalogo import (
    leer_companias, guardar_companias, obtener_nombre_compania,
    leer_activos, guardar_activos,
)
from .config import logger, SOL_DIR, LOGS_DIR
