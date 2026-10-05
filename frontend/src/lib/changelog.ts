// Version y contenido de "Novedades". Igual que precarga usa core/config.py
// VERSION, aqui la version vive en el frontend porque la app no expone una
// ruta de version. Al hacer un release, incrementarla para que el modal
// vuelva a mostrarse una vez por usuario.
export const VERSION = '0.5'

export interface Cambio {
  icono: string
  titulo: string
  detalle: string
}

// Lo mas reciente debe ir primero.
export const CAMBIOS: Cambio[] = [
  {
    icono: '🚀',
    titulo: 'Rendimiento',
    detalle:
      'Conexion persistente (keep-alive) a Supabase y el personal de cada solicitud se inserta en lotes en vez de uno por uno. Guardar una solicitud paso de abrir una conexion TLS por persona a reutilizar la misma.',
  },
  {
    icono: '🗂️',
    titulo: 'Procesar varios PDF',
    detalle:
      'Procesar PDF ahora acepta y procesa varios archivos a la vez, con estado por archivo y descarga automatica del Excel generado.',
  },
  {
    icono: '🔍',
    titulo: 'Busqueda global Ctrl+K',
    detalle:
      'La barra de busqueda del encabezado, antes decorativa, ahora abre una paleta real (Ctrl+K / Cmd+K) para buscar solicitudes y activos.',
  },
  {
    icono: '📅',
    titulo: 'Fechas de las plantillas',
    detalle:
      'En Entradas C18 y en el campo Fecha de Solicitud se usa la fecha de llegada real del personal, no la del dia en que se abre la plantilla. En Salidas C18 se usa TODAY().',
  },
  {
    icono: '📍',
    titulo: 'Destino en A12',
    detalle:
      'La celda A12 se rellena automaticamente: RPX → REFORMA PEMEX, CPZ → U.H.F "CERRO DE LA PEZ".',
  },
  {
    icono: '📊',
    titulo: 'Dashboard',
    detalle:
      'Las tarjetas Alto/Bajo ahora cuadran con la grafica: Altas + Bajas = Total Movimientos. Grafica con cuatro series (RPX altas, RPX bajas, CPZ altas, CPZ bajas) seleccionables.',
  },
]
