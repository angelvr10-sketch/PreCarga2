from .procesador import (
    llenar_plantilla, extraer_personal_baja,
    listar_solicitudes_xlsx, leer_meta_xlsx,
    llenar_plantilla_salidas, llenar_plantilla_entrada,
    leer_personal_de_xlsx, generar_plantilla_desde_bd,
)
from .catalogo import (
    obtener_nombre_compania, indice_companias, contiene_activo,
    leer_activos, invalidar_cache,
)
from .config import logger, SOL_DIR, LOGS_DIR
